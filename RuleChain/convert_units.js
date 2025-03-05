var newMsg = {};
var conversions = {
    "eye_temp": function(v) { return v / 100; },           // m°C to °C
    "eye_temp_2": function(v) { return v / 100; },
    "eye_temp_3": function(v) { return v / 100; },
    "eye_temp_4": function(v) { return v / 100; },
    "ble_temp_1": function(v) { return v !== 32767 ? v / 100 : v; },  // m°C to °C, skip inactive
    "ble_temp_2": function(v) { return v !== 32767 ? v / 100 : v; },
    "ble_temp_3": function(v) { return v !== 32767 ? v / 100 : v; },
    "ble_temp_4": function(v) { return v !== 32767 ? v / 100 : v; },
    "external_voltage": function(v) { return v / 1000; },  // mV to V
    "battery_voltage": function(v) { return v / 1000; },   // mV to V
    "battery_current": function(v) { return v / 1000; },   // mA to A
    "eye_battery_level": function(v) { return v / 1000; }, // mV to V
    "eye_battery_level_2": function(v) { return v / 1000; },
    "eye_battery_level_3": function(v) { return v / 1000; },
    "eye_battery_level_4": function(v) { return v / 1000; }
};

var telemetry = msg.msg || msg;
for (var key in telemetry) {
    if (telemetry.hasOwnProperty(key)) {
        newMsg[key] = conversions[key] ? conversions[key](telemetry[key]) : telemetry[key];
    }
}

return {msg: newMsg, metadata: metadata, msgType: msgType};