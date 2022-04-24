# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import json
from time import time
import time
from awscrt import io
from awscrt import mqtt
from awsiot import mqtt_connection_builder
from uuid import uuid4

# This sample is similar to `samples/basic_connect.py` but the private key
# for mutual TLS is stored on a PKCS#11 compatible smart card or
# Hardware Security Module (HSM).
#
# See `samples/README.md` for instructions on setting up your PKCS#11 device
# to run this sample.
#
# WARNING: Unix only. Currently, TLS integration with PKCS#11 is only available on Unix devices.

# Parse arguments
import command_line_utils
cmdUtils = command_line_utils.CommandLineUtils("PKCS11 Connect - Make a MQTT connection using PKCS11.")
cmdUtils.add_common_mqtt_commands()
cmdUtils.add_common_proxy_commands()
cmdUtils.add_common_logging_commands()
cmdUtils.register_command("cert", "<path>", "Path to your client certificate in PEM format.", True, str)
cmdUtils.register_command("client_id", "<str>",
                          "Client ID to use for MQTT connection (optional, default='test-*').",
                          default="test-" + str(uuid4()))
cmdUtils.register_command("port", "<port>",
                          "Connection port. AWS IoT supports 433 and 8883 (optional, default=auto).",
                          type=int)
cmdUtils.register_command("pkcs11_lib", "<path>", "Path to PKCS#11 Library", required=True)
cmdUtils.register_command("pin", "<str>", "User PIN for logging into PKCS#11 token.", required=True)
cmdUtils.register_command("token_label", "<str>", "Label of the PKCS#11 token to use (optional).")
cmdUtils.register_command("slot_id", "<int>", "Slot ID containing the PKCS#11 token to use (optional).", False, int)
cmdUtils.register_command("key_label", "<str>", "Label of private key on the PKCS#11 token (optional).")
cmdUtils.register_command("pub_topic","<topic>","This topic is appended to <client_id>/", required=False, default="testing")
cmdUtils.register_command("sub_topic","<topic>","This topic is appended to <client_id>/", required=False, default="testing")
cmdUtils.register_command("payload","<payload>","This message is sent to the AWS IoT Core", required=False, default="Hello, World!")
cmdUtils.register_command("num_pub","<num>","Number of publish packets", False, int, default=25)
cmdUtils.register_command("delay_secs","<num>","Number of seconds to wait between publishes", False, int, default=2)

# Needs to be called so the command utils parse the commands
cmdUtils.get_args()

# Callback when connection is accidentally lost.
def on_connection_interrupted(connection, error, **kwargs):
    print("Connection interrupted. error: {}".format(error))

# Callback when an interrupted connection is re-established.
def on_connection_resumed(connection, return_code, session_present, **kwargs):
    print("Connection resumed. return_code: {} session_present: {}".format(return_code, session_present))

# Callback when the subscribed topic receives a message
def on_message_received(topic, payload, dup, qos, retain, **kwargs):
    print("Received message from topic '{}': {}".format(topic, payload))

sample_pub_topic = "$aws/things/" + cmdUtils.get_command("client_id") + "/" + "shadow/" + cmdUtils.get_command("pub_topic")
sample_sub_topic = "$aws/things/" + cmdUtils.get_command("client_id") + "/" + "shadow/" + cmdUtils.get_command("sub_topic")
sample_payload = cmdUtils.get_command("payload")
sample_count = cmdUtils.get_command("num_pub")
sample_delay_secs = cmdUtils.get_command("delay_secs")

if __name__ == '__main__':
    # Create a connection using websockets.
    # Note: The data for the connection is gotten from cmdUtils.
    # (see build_pkcs11_mqtt_connection for implementation)
    mqtt_connection = cmdUtils.build_pkcs11_mqtt_connection(on_connection_interrupted, on_connection_resumed)

    print("Connecting to {} with client ID '{}'...".format(
        cmdUtils.get_command("endpoint"), cmdUtils.get_command("client_id")))

    connect_future = mqtt_connection.connect()

    # Future.result() waits until a result is available
    connect_future.result()
    print("Connected!")

    # Subscribe to a topic here
    print("Subscribing to topic '{}'...".format(sample_sub_topic))
    subscribe_future, packet_id = mqtt_connection.subscribe(
        topic=sample_sub_topic,
        qos=mqtt.QoS.AT_LEAST_ONCE,
        callback=on_message_received)

    subscribe_result = subscribe_future.result()
    print("Subscribed with {}".format(str(subscribe_result['qos'])))

    # Do some publishing here - we will use a simple "Hello, World!" if not supplied by user
    looper = 0
    for looper in range(0,sample_count):
        print("Publishing to topic {}...".format(sample_pub_topic))
        sample_json = json.dumps(sample_payload + ": " + str(looper+1))
        mqtt_connection.publish(sample_pub_topic,sample_json,qos=mqtt.QoS.AT_LEAST_ONCE)
        time.sleep(sample_delay_secs)

    # Disconnect
    print("Disconnecting...")
    disconnect_future = mqtt_connection.disconnect()
    disconnect_future.result()
    print("Disconnected!")
