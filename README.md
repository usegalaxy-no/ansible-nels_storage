NeLS Storage import/export tools
================================

An [Ansible][ansible] role for installing and configuring tools for transferring datasets between the [NeLS Storage][nelsportal] and a [Galaxy][galaxyproject] server.
The role will install two tools (import and export) plus a common configuration file which must be configured against either the production or test storage using variables described below.
The file permissions for the configuration file will be '440', but it must be readable by the system user that runs the tool jobs.
Note that the role will not automatically add the new tools to any of Galaxy's toolbox configuration files, so this must be handled in another way.
One convenient way is to set the optional "nels_storage_tool_conf_dir" variable. This will then create a new toolbox configuration file which can be referenced in "galaxy.yml".

[ansible]: http://www.ansible.com/
[galaxyproject]: https://galaxyproject.org/
[nelsportal]: https://nels.bioinfo.no/

in requirements:

    - src: https://github.com/usegalaxy-no/ansible-role-tos-api.git
      name: usegalaxy-no.tos-api

Role Variables
--------------

### Install locations ###

These variables control where the tools and configuration files will be installed on the Galaxy server. No defaults are provided.
Note that this role will _not_ create any new directories, so all the locations referred to by the variables below must already exist.

- `nels_storage_import_tool_dir`: Directory on the Galaxy server where the import tool (wrapper and script) will be installed. The original location was "tools/data_source".
- `nels_storage_export_tool_dir`: Directory on the Galaxy server where the export tool (wrappers and script) will be installed. The original location was "tools/data_destination".
- `nels_storage_config_dir`: Directory on the Galaxy server where the configuration file will be installed. 
   This ***must*** be the same directory as the magic `$GALAXY_DATA_INDEX_DIR` variable available to tool wrappers, which is configured by the "tool_data_path" setting in "galaxy.yml".
- `nels_storage_tool_conf_dir` (optional): If provided, a tool config file named "nels_tool_conf.xml" containing entries for the import and export tools will be placed in this directory.
   This file can then be added to the "tool_config_file`" setting in "galaxy.yml" .


### NeLS Storage configuration ###

The following variables define entry points and access credentials for the NeLS Storage.
The settings will vary depending on whether you want to connect to the production instance or test instance of the NeLS Storage.

- `nels_storage_url`: The URL pointing to the 'welcome' page of the NeLS Storage.
- `nels_storage_api_url`: The API entry point for the NeLS Storage.
- `nels_storage_client_key`: A 'username' used to authenticate against the NeLS Storage.
- `nels_storage_client_secret`: A 'password' used to authenticate against the NeLS Storage. This should be placed in the vault!
