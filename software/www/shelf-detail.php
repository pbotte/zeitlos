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
    <link rel="shortcut icon" href="/favicon.ico" type="image/x-icon">
    <link rel="icon" href="/favicon.ico" type="image/x-icon">
    <title>Shop Shelf</title>
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
            console.log("MQTT Connection Failed");
            connected_flag = 0;
        }
        function onMessageArrived(r_message) {
            // Message: r_message.payloadString
            // Topic: r_message.destinationName;
            //console.log("MQTT recv (" + r_message.destinationName + "): ", r_message.payloadString);

            var shelfID = <?php echo $shelfID; ?>;
            var obj = JSON.parse(r_message.payloadString);
            var actProductPos = 0;

            if (r_message.destinationName == 'homie/shopController/productsToDisplayOnShelf/'+shelfID+'/products') {
                obj.forEach(elem => {
                    //console.log(elem); 
                    var strUnit = '?';
                    var strUnit2 = '?';
                    if (obj[actProductPos].Pricing.Type == 1) {
                        strUnit = 'Stk';
                        strUnit2 = 'Stk';
                    } else {
                        strUnit = 'g';
                        strUnit2 = 'g';
                        if (obj[actProductPos].Pricing.GrammsPerUnit == 1000) {
                            strUnit = 'kg';
                        }
                        if (obj[actProductPos].Pricing.GrammsPerUnit == 100) {
                            strUnit = '100 g';
                        }
                    } 
                    var withdrawal = obj[actProductPos].UnitsAtBegin-obj[actProductPos].UnitsCurrent;
                    var myprice = withdrawal * obj[actProductPos].Pricing.PricePerUnit;
                    document.getElementById("product"+actProductPos+"_ProductName").innerHTML = obj[actProductPos].ProductName;
                    document.getElementById("product"+actProductPos+"_ProductDescription").innerHTML = obj[actProductPos].ProductDescription;
                    document.getElementById("product"+actProductPos+"_UnitsAtBegin").innerHTML = 'anfänglich vorhanden: '+obj[actProductPos].UnitsAtBegin+' '+strUnit2;
                    document.getElementById("product"+actProductPos+"_UnitsCurrent").innerHTML = 'Rest: '+obj[actProductPos].UnitsCurrent+' '+strUnit2;
                    document.getElementById("product"+actProductPos+"_UnitsWithdrawal").innerHTML = 'entnommen: '+(withdrawal).toString()+' '+strUnit2;
                    document.getElementById("product"+actProductPos+"_UnitPrice").innerHTML = 'Einheitspreis: '+obj[actProductPos].Pricing.PricePerUnit.toLocaleString('de-DE', { 
  style                    : 'decimal', minimumFractionDigits    : 2, maximumFractionDigits    : 2})+' € / '+strUnit;
                    document.getElementById("product"+actProductPos+"_price").innerHTML = 'Preis: '+myprice.toLocaleString('de-DE', { 
  style                    : 'decimal', minimumFractionDigits    : 2, maximumFractionDigits    : 2})+' €';
                    document.getElementById("product"+actProductPos+"_img").src = obj[actProductPos].Picture;
                    actProductPos++;
                }
                );
            }

        }

        function onConnected(recon, url) {
            console.log(" in onConnected " + reconn);
            mqtt_warning_off();
        }

        function onConnect() {
            mqtt_warning_off();
            console.log("Connected to " + host + ":" + port);
            connected_flag = 1
            console.log("connected_flag= ", connected_flag);
            mqtt.subscribe("homie/shopController/productsToDisplayOnShelf/<?php echo $shelfID?>/#");
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

<body>
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
    <div id="overlay">
        <div id="text">Error:<br>no connection to MQTT server</div>
    </div>

    <h1>Warenregal</h1>

    <table style="width: 100%;" border="0">
        <tbody>
            <tr>
                <?php for ($i=0; $i<3; $i++) {?>
                <td style="vertical-align: top; width: 33%;">
                    <p><b><span id="product<?php echo $i; ?>_ProductName"></span></b></p>
                    <p><span id="product<?php echo $i; ?>_ProductDescription"></span></p>
                    <p><span id="product<?php echo $i; ?>_UnitsAtBegin"></span></p>
                    <p><span id="product<?php echo $i; ?>_UnitsCurrent"></span></p>
                    <p><span id="product<?php echo $i; ?>_UnitsWithdrawal"></span></p>
                    <p><span id="product<?php echo $i; ?>_UnitPrice"></span></p>
                    <p><span id="product<?php echo $i; ?>_price"></span></p>
                    <img width="100%" src="" id="product<?php echo $i; ?>_img">
                </td>
                <?php } ?>
            </tr>
        </tbody>
    </table>

    <script>
        var connected_flag = 0;
        var host = "192.168.10.10"; //shop-master
        var port = 8123;
        console.log("Set up the MQTT client (clientshelf<?php echo $shelfID;?>) to connect to " + host + ":" + port);
        var mqtt = new Paho.MQTT.Client(host, port, "clientshelf<?php echo "$shelfID$debugClientStrSuffix";?>");
        mqtt.onConnectionLost = onConnectionLost;
        mqtt.onMessageArrived = onMessageArrived;
        mqtt.onConnected = onConnected;


        mqtt_warning_on();
        MQTTconnect();
        
        setInterval(function () { if (connected_flag == 0) MQTTconnect() }, 5 * 1000);
    </script>

</body>

</html>
