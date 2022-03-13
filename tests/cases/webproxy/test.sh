set -e
rm -rf artifacts
mkdir -p artifacts

public_port=$(../../common/find-free-port)
private_port=$(../../common/find-free-port)

printf "Starting server on port $private_port\n"
PYTHONUNBUFFERED=1 SPOKEPORT=$private_port spoke-server &
SERVER_PID=$!

printf "Sending persistent messages to server\n"
PYTHONUNBUFFERED=1 SPOKEPORT=$private_port spoke-publish -p foo 5

sleep 0.2

printf "Starting webproxy on port $public_port\n"
PYTHONUNBUFFERED=1 spoke-webproxy --private-port $private_port --public-port $public_port --cert ../../common/localhost.pem foo &
WEBPROXY_PID=$!

sleep 0.2

printf "Starting echo client on web proxy\n"
PYTHONUNBUFFERED=1 SPOKEPORT=$public_port python echo_client.py >& artifacts/echo_client.txt &
ECHO_PID=$!

printf "Giving echo client time to start up\n"
sleep 0.2

printf "Publishing to proxied channel on private server (should be visible)\n"
PYTHONUNBUFFERED=1 SPOKEPORT=$private_port spoke-publish foo 10

sleep 0.2

printf "Sending SIGTERM to everything\n"
kill -15 $SERVER_PID $WEBPROXY_PID $ECHO_PID

printf "Waiting for everything to shutdown\n"
wait

printf "Diffing output - <got >exp\n"
diff -r artifacts expected
exitcode=$?

exit $exitcode
