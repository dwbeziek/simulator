// Extract 'reported' from 'state'
var data = msg.state && msg.state.reported ? msg.state.reported : msg;
var newMsg = {};

// Flatten all keys from 'reported' into top-level
for (var key in data) {
    if (data.hasOwnProperty(key)) {
        newMsg[key] = data[key];
    }
}

return {msg: newMsg, metadata: metadata, msgType: msgType};