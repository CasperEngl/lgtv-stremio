#!/bin/sh
# tv-luna.sh <uri> <json> [seconds]: one bus call as the Developer Mode user; -i because -n 1 exits before the reply prints
exec "$(dirname "$0")/tv-ssh.sh" "(luna-send-pub -i '$1' '$2' & sleep ${3:-3}; kill \$!) 2>&1"
