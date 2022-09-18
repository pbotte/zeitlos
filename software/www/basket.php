<?php
$shelfID = 1;
if (array_key_exists('shelfid', $_GET)) {
	$shelfID = intval($_GET['shelfid']);
}
$debugClientStrSuffix = "";
if (array_key_exists('debug', $_GET)) {
	$debugClientStrSuffix = 'debug';
}
?>
<html xmlns="http://www.w3.org/1999/xhtml">

<head>
    <style>
        #overlay {
            position: fixed;
            display: none;
            width: 100%;
            height: 100%;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #CE1510;
            z-index: 2;
        }
        #text{
            position: absolute;
            top: 50%;
            left: 50%;
            font-size: 50px;
            color: white;
            transform: translate(-50%,-50%);
            -ms-transform: translate(-50%,-50%);

        }
    </style>
    <script>
    function mqtt_warning_on() {
        document.getElementById("overlay").style.display = "block";
    }
    function mqtt_warning_off() {
        document.getElementById("overlay").style.display = "none";
    }
    </script>

<!--Show the following sign until a MQTT connection is establised-->
    <div id="overlay" style="display:block">
        <div id="text">Error:<br>no connection to MQTT server</div>
    </div>


    <title>Basket</title>
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<!--For the plain library-->
	<!--<script src="https://cdnjs.cloudflare.com/ajax/libs/paho-mqtt/1.0.1/mqttws31.js" type="text/javascript"></script>-->
	<!--For the minified library: -->
	<!--<script src="https://cdnjs.cloudflare.com/ajax/libs/paho-mqtt/1.0.1/mqttws31.min.js" type="text/javascript"></script>-->
	<script src="/mqttws31.min.js" type="text/javascript"></script>

	<script type="text/javascript">


		function onConnectionLost() {
            mqtt_warning_on();
			console.log("connection lost");
			connected_flag = 0;
		}
		function onFailure(message) {
            mqtt_warning_on();
			console.log("Failed");
			connected_flag = 0;
        }
        function isEmpty(obj) {
            for(var prop in obj) {
                if(obj.hasOwnProperty(prop)) {
                    return false;
                }
            }
            return JSON.stringify(obj) === JSON.stringify({});
        }
		function onMessageArrived(r_message) {
            //console.log("MQTT recv (" + r_message.destinationName + "): ", r_message.payloadString);
            
            if (r_message.destinationName == "homie/shop_controller/actualBasket") {
                var obj = JSON.parse(r_message.payloadString);
                //console.log(obj);
                var mstr = '';
                if (! isEmpty(obj['data'])) {
                    Object.values(obj['data']).forEach(element => {
                     mstr += '<tr><td style="width: 33%;">'+element['ProductName']+'</td>'+
                        '<td style="width: 33%; text-align: right; text-align: center;">'+element['withdrawal_units']+' </td>'+
                        '<td style="width: 34%; text-align: right;">'+element['price'].toLocaleString('de-DE', { 
  style                    : 'decimal', minimumFractionDigits    : 2, maximumFractionDigits    : 2})+'</td>'+
                        '</tr>\n';
                    }
                    );
                } else {
                    mstr += '<tr><td colspan="3">Noch keine Produkte entnommen.<br>&nbsp;<br>&nbsp;</td></tr>\n';
                }
                mstr += '<tr>'+
                    '<td style="width: 33%; vertical-align: bottom;" colspan="2"><strong>Summe:</strong></td>'+
                    '<td style="width: 34%; text-align: right; vertical-align: bottom;"><br /><br /><strong>'+obj['total'].toLocaleString('de-DE', { 
  style                    : 'decimal', minimumFractionDigits    : 2, maximumFractionDigits    : 2}) +'</strong></td>'+
                    '</tr>';
                document.getElementById("myBasketTable").innerHTML = mstr;
            }
		}

		function onConnected(recon, url) {
            mqtt_warning_off();
			console.log(" in onConnected " + reconn);
		}

		function onConnect() {
            mqtt_warning_off();
			console.log("Connected to " + host + ":" + port);
			connected_flag = 1
			console.log("connected_flag= ", connected_flag);
			mqtt.subscribe("homie/shop_controller/actualBasket");
		}

		function MQTTconnect() {
            console.log("MQTT start connecting");
            var options = {
                timeout: 3,
                onSuccess: onConnect,
                onFailure: onFailure,
            };

            mqtt.connect(options);
            return false;
        }
	</script>

</head>

<style>
h1 {
font-family: Tahoma, Geneva, sans-serif;
font-size: 150px;
letter-spacing: 2px;
word-spacing: 2px;
color: #000000;
font-weight: 700;
text-decoration: none;
font-style: normal;
font-variant: normal;
text-transform: none;
}

td {
font-family: Tahoma, Geneva, sans-serif;
font-size: 40px;
letter-spacing: 2px;
word-spacing: 2px;
color: #000000;
font-weight: 400;
text-decoration: none;
font-style: normal;
font-variant: normal;
text-transform: none;
}

table.paleBlueRows {
  font-family: Tahoma, Geneva, sans-serif;
  border: 1px solid #FFFFFF;
  width: 350px;
  height: 200px;
  border-collapse: collapse;
}
table.paleBlueRows td, table.paleBlueRows th {
  border: 0px solid #000000;
  padding: 3px 2px;
}
table.paleBlueRows tbody td {
  font-size: 30px;
}
table.paleBlueRows tr:nth-child(even) {
  background: #D0E4F5;
}
table.paleBlueRows thead {
  background: #0B6FA4;
  border-bottom: 5px solid #FFFFFF;
}
table.paleBlueRows thead th {
  font-size: 23px;
  font-weight: bold;
  color: #FFFFFF;
  border-left: 2px solid #FFFFFF;
}
table.paleBlueRows thead th:first-child {
  border-left: none;
}

table.paleBlueRows tfoot {
  font-size: 30px;
  font-weight: bold;
  color: #333333;
  background: #D0E4F5;
  border-top: 3px solid #444444;
}
table.paleBlueRows tfoot td {
  font-size: 30px;
}
</style>

<body>
	<h1>Warenkorb</h1>

    <table border="1" style="border-collapse: collapse; width: 100%;" class="paleBlueRows">
    <thead>
    <tr>
    <td style="width: 33%; background-color: blue;"><span style="color: #ffffff;"><strong>Produkt</strong></span></td>
    <td style="width: 33%; background-color: blue; text-align: center;"><span style="color: #ffffff;""><strong>Menge</strong></span></td>
    <td style="width: 34%; background-color: blue; text-align: right;"><span style="color: #ffffff;"><strong>Preis in &euro;</strong></span></td>
    </tr>
    </thead>
    <tbody id="myBasketTable">
    </tbody>
    </table>
    <p></p>


	<script>
		var connected_flag = 0;
        var host = "192.168.10.10"; //shop-master
        var port = 9001;
        console.log("Set up the MQTT client to connect to " + host + ":" + port+ " as clientbasket<?php echo "$shelfID$debugClientStrSuffix"; ?>");
        var mqtt = new Paho.MQTT.Client(host, port, "clientbasket<?php echo "$shelfID$debugClientStrSuffix"; ?>");
        mqtt.onConnectionLost = onConnectionLost;
        mqtt.onMessageArrived = onMessageArrived;
        mqtt.onConnected = onConnected;

        mqtt_warning_on();

        MQTTconnect();
		setInterval(function () { if (connected_flag == 0) MQTTconnect() }, 5 * 1000);
	</script>

</body>

</html>
