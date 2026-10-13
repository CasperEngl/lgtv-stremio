#!/bin/sh
# tv-ssh.sh <command>: run one command on the set as the Developer Mode user.
# The address comes from ~/.ssh/known_hosts_webos (one entry); the key is ~/.ssh/webos_${SET:-g5}.
H=$(awk '{print $1}' "$HOME/.ssh/known_hosts_webos" | sed -E 's/\[(.*)\]:9922/\1/')
exec ssh -p 9922 -i "$HOME/.ssh/webos_${SET:-g5}" -o IdentitiesOnly=yes -o UserKnownHostsFile="$HOME/.ssh/known_hosts_webos" -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa -o LogLevel=ERROR -o ConnectTimeout=8 "prisoner@$H" "$@"
