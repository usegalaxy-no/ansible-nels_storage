import optparse, os
import configparser
import galaxy.util.json as json
import sys

import requests
from requests.auth import HTTPBasicAuth

#import galaxy.model # need to import model before sniff to resolve a circular import dependency
#from galaxy.datatypes import sniff
#from galaxy.datatypes.registry import Registry

VALID_CHARS = '.-()[]0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ '

# The following two lists define file suffixes for supported compression formats and which data formats that are allowed to be compressed.
# Datasets that have double file suffixes from these two groups (e.g. ".fastq.gz" or ".fastqsanger.bz2") will have their Galaxy datatype based on both (rather than just ".gz")
compressed_format_suffix = ["gz","bz2"]
compressable_formats = ["fastq","fastqsanger","fastqcssanger","fastqsolexa","fastqillumina","fq"]
decompress_command = {"gz":"gunzip","bz2":"bzip2 -d"}

# This is a hack to convert certain file suffixes on-the-fly to data types that are recognized by Galaxy
convert_suffix = {"bb":"bigbed","bw":"bigwig","fq":"fastq","fq.gz":"fastq.gz"}

#from nels.storage_client.config import config as storage_config
#from nels import storage_client

def configure_api_connection(galaxy_tool_data_dir):
    parser = configparser.RawConfigParser()
    parser.read(galaxy_tool_data_dir + '/nels_storage_config.loc')
    api_url = parser.get("Parameters","API_URL")
    client_key = parser.get("Parameters","CLIENT_KEY")
    client_secret = parser.get("Parameters","CLIENT_SECRET")
    return api_url, client_key, client_secret


def get_ssh_credential(nels_id, api_url, client_key, client_secret):
    url = api_url+ "/users/" + nels_id
    response =  requests.get(url, auth=(client_key, client_secret))
    if(response.status_code == requests.codes.ok):
        json_response = response.json()
        return [json_response['hostname'],json_response['username'],json_response['key-rsa']]
    else:
        raise Exception("HTTP response code=%s" % str(response.status_code))


def download_from_nels_importer( json_parameter_file, galaxy_tool_data_dir ):
    json_params = json.from_json_string( open( json_parameter_file, 'r' ).read() ) # leser inn fila som inneholder param_dict, output_data og job_config bla.
    datasource_params = json_params.get( 'param_dict' ) # henter ut paramdict
    nelsId = datasource_params.get( "nelsId", None ) # henter gs-brukernavn fra paramDict 
    output_filename = datasource_params.get( "output", None ) # outputFilename 
    dataset_id = json_params['output_data'][0]['dataset_id'] # dataset_id fra output_data
    hda_id = json_params['output_data'][0]['hda_id'] # # hda_id fra output_data
    datasetsDir = output_filename[:output_filename.rfind('/')+1]

    #get ssh storage - credentails of the user
    api_url, client_key, client_secret = configure_api_connection(galaxy_tool_data_dir)
    [host,username,sshKey] = get_ssh_credential(nelsId, api_url, client_key, client_secret)

    sshFn = os.path.join( os.getcwd(), '%s.txt' % username )
    with open(sshFn, 'w') as sshFile:
        sshFile.write(sshKey)
    os.system('chmod 0600 %s'% sshFn)

    filePathList = datasource_params['selectedFiles'].replace(' ', '\ ').split(',')
    if isinstance(filePathList, str):
        filePathList = [filePathList]
    #print filePathList    
    metadata_parameter_file = open( json_params['job_config']['TOOL_PROVIDED_JOB_METADATA_FILE'], 'w' )

    used_filenames = []

    for filePath in filePathList:
        filename = filePath.split('/')[-1] if filePath.find('/')>=0 else filePath
        filename = filename.replace('\ ', ' ')
        compression = ""

        if filename.count('.')>=2 and filename.split('.')[-1] in compressed_format_suffix:
            # The file is compressed and has a double suffix (e.g. ".fastq.gz"). If the compressed format is supported, keep the file compressed and use both suffixes to set the data type
            # If the compressed format is not supported, use the second to last suffix as the data type and decompress the file after transferring it to the Galaxy server
            if filename.split('.')[-2] in compressable_formats:
                galaxy_ext = '.'.join(filename.split('.')[-2:]) # data type = last two suffixes
                filename   = '.'.join(filename.split('.')[:-2])  # filename = everything except last two suffixes
            else:
                compression = filename.split('.')[-1]  # compression format = last suffix
                galaxy_ext  = filename.split('.')[-2] # data type = second to last suffix
                filename = '.'.join(filename.split('.')[:-2]) # filename = everything except last two suffixes
        elif filename.find('.') > 0:
            galaxy_ext = filename.split('.')[-1]
            filename = '.'.join(filename.split('.')[:-1])
            if galaxy_ext in compressed_format_suffix:
                compression = galaxy_ext
                galaxy_ext = 'unknown'  # This is not a recognized data type, but the user can change it manually later
        else:
            galaxy_ext = 'unknown'

        if (galaxy_ext in convert_suffix):
            galaxy_ext = convert_suffix[galaxy_ext]

        if output_filename is None:
            original_filename = filename
            filename = ''.join( c in VALID_CHARS and c or '-' for c in filename )
            while filename in used_filenames:
                filename = "-%s" % filename
            used_filenames.append( filename )
            output_filename = 'primary_%i_%s_visible_%s' % ( hda_id, filename, galaxy_ext ) # in versions up to 16.10, the current working directory 'os.getcwd()' was added as path-prefix, but this would fail in v17.09 and it was therefore removed
            metadata_parameter_file.write( "%s\n" % json.to_json_string( dict( type = 'new_primary_dataset',
                                     base_dataset_id = dataset_id,
                                     ext = galaxy_ext,
                                     filename = output_filename,
                                     #name = "NELS import on %s" % ( original_filename ) ) ) )
                                     name = original_filename ) ) )
        else: # first iteration
            if dataset_id is not None:
               metadata_parameter_file.write( "%s\n" % json.to_json_string( dict( type = 'dataset',
                                     dataset_id = dataset_id,
                                     ext = galaxy_ext,
                                     #name = "NELS import on %s" % ( filename ) ) ) )
                                     name = filename ) ) )
        #print 'scp -o BatchMode=yes -i %s "%s@%s:%s" "%s" ' % (sshFn, username, host, filePath, output_filename)
        os.system('scp -o BatchMode=yes -i %s "%s@%s:%s" "%s" ' % (sshFn, username, host, filePath, output_filename))
        if compression:
            os.system('mv "%s" "%s.%s"' % (output_filename, output_filename, compression)) # add the compressed format suffix back to the filename (or else the decompression command may complain)
            os.system('%s "%s.%s"' % (decompress_command[compression], output_filename, compression)) # decompress the file. This will remove the compression suffix that was added on the previous line from the filename
        os.chmod(output_filename, 0o644)
        output_filename = None # only have one filename available

    metadata_parameter_file.close()
    os.remove(sshFn)
    return True

if __name__ == '__main__':
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( '-d', '--galaxy_tool_data_dir', dest='galaxy_tool_data_dir', action='store', type="string", default=None, help='galaxy_tool_data_dir' )
    parser.add_option( '-p', '--json_parameter_file', dest='json_parameter_file', action='store', type="string", default=None, help='json_parameter_file' )
    (options, args) = parser.parse_args()
    download_from_nels_importer( options.json_parameter_file, options.galaxy_tool_data_dir )
