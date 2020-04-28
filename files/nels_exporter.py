import os
import configparser
import sys
import requests
from requests.auth import HTTPBasicAuth

# import galaxy.model # need to import model before sniff to resolve a circular import dependency

DEFAULT_GALAXY_EXT = "data"
VALID_CHARS = '.-()[]0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ '
  
def histLabelWithExt(histItem):
    label, ext = histItem[1:]
    if label.endswith('.' + ext):
        return label
    return '.'.join([label, ext])


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
    

def uploadToNels(galaxyToolDataDir, filePath, nelsId, outfn, histItems):
    datasetsDir = '/'.join(histItems[0][0].split('/')[:-1]) + '/'
    api_url, client_key, client_secret = configure_api_connection(galaxyToolDataDir)
    [host,username,sshKey] = get_ssh_credential(nelsId, api_url, client_key, client_secret)

    if filePath[-1] !='/':
        filePath += '/'
    sshKeyFn = os.path.join( os.getcwd(), '%s.txt' % username )
    with open(sshKeyFn, 'w') as sshObj:
        sshObj.write(sshKey)
        os.system('chmod 0600 '+sshKeyFn)
    
    with open(outfn, 'w') as outFileObj: 
        for histItem in histItems:
            transferFileToNels(histItem, filePath, sshKeyFn, username,host)
            outFileObj.write('Transferred "%s" to my area at NELS ( "%s" ) <br/>' % (histLabelWithExt(histItem), filePath))
            
    os.remove(sshKeyFn)
    return True

    
def transferFileToNels(histItem, filePath, sshKeyFn, username,host):
    histFile = histItem[0]
    label = requests.utils.quote(histLabelWithExt(histItem), safe=' ')
    destFile = (filePath+label).replace('//','/').replace(' ','\ ')
    os.system( 'scp -o BatchMode=yes -i %s %s "%s@%s:%s"' % (sshKeyFn, histFile, username, host, destFile) )

    
def checkArguments(argList):
    argSize = len(argList)
    if argSize<8 or (argSize-5)%3 != 0:
        outFn = argList[4]

        with open(outFn,'w') as outFile:
            outFile.write( 'No history elements selected to be exported to NELS repository<br/>Please rerun the tool ' \
                            'and select at least 1 dataset to be exported form your history to the central repository' \
                            '<br/><br/>Arguments for run:<br/>' )

            labels = ['Galaxy tool-data path', 'tool used', 'remote file path', 'nelsId', 'output file path']
            outFile.write('<br/> '.join(['%s: %s'%(labels[i], argList[i]) for i in range(min(argSize, len(labels)))])+'<br/>')

            if argSize>5:
                outFile.write('Selected datasets for export: '+repr(argList[5:]))

        return False
    
    return True


if __name__ == '__main__':
    import sys
    
    if checkArguments(sys.argv):
        galaxyToolDataDir = sys.argv[1]
        filePath, nelsId, outFn = sys.argv[2:5]
        histItems = [(sys.argv[i], sys.argv[i+1], sys.argv[i+2]) for i in range(5, len(sys.argv), 3)]
        uploadToNels(galaxyToolDataDir, filePath, nelsId, outFn, histItems)
