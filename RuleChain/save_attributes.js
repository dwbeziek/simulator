var topic = metadata.topic; // Get the MQTT topic
var imei = topic.split("/")[1]; // Extract IMEI from topic structure

metadata.imei = imei; // Attach IMEI to metadata
return { metadata: metadata, msg: msg };