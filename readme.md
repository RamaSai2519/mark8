Commands to refresh the git submodules.
 - git submodule deinit --all --force
 - git submodule update --init --recursive

Command to redeploy everything.
 - cd mark8 && git pull && git submodule deinit --all --force && git submodule update --init --recursive && cd ../ARK-I && git pull && git submodule deinit --all --force && git submodule update --init --recursive && pm2 restart all && cd .. && pm2 logs