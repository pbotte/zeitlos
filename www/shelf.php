<?php
$shelfID = 1;
if (array_key_exists('shelfid', $_GET)) {
	$shelfID = intval($_GET['shelfid']);
}
?>
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE html
    PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<style>
    #status {
        background-color: red;
        font-size: 4;
        font-weight: bold;
        color: white;
        line-height: 140%;
    }
</style>

<head>
    <link rel="shortcut icon" href="/favicon.ico" type="image/x-icon">
    <link rel="icon" href="/favicon.ico" type="image/x-icon">
    <title>Websockets Using JavaScript MQTT Client</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!--For the plain library-->
    <!--<script src="https://cdnjs.cloudflare.com/ajax/libs/paho-mqtt/1.0.1/mqttws31.js" type="text/javascript"></script>-->
    <!--For the minified library: -->
    <!--<script src="https://cdnjs.cloudflare.com/ajax/libs/paho-mqtt/1.0.1/mqttws31.min.js" type="text/javascript"></script>-->
    <script src="/mqttws31.min.js" type="text/javascript"></script>


	<script>
var data_scales = [
    {
        SerialNumber: "0x57383735393215170b03", 
        DisplayRounding: 5, 
        GlobalOffset: 1899.45, 
        Offset: [41308, -239592, -8747, 26511], 
        Slope: [-0.004746168, 0.004798805, -0.004741381, 0.004679427],
        shelf: "shop-shelf-01",
        ProductID: 0,
        UnitsAtBegin: 0,
        UnitsCurrent: 0
    },
    {
        SerialNumber: "0x59363332393115171b11", 
        DisplayRounding: 5, 
        GlobalOffset: 1913.963, 
        Offset: [54148.9, 140098.6, -147084.4, 155639.7], 
        Slope: [-0.004463, 0.004501, -0.004461, 0.004465],
        shelf: "shop-shelf-02",
        ProductID: 1,
        UnitsAtBegin: 0,
        UnitsCurrent: 0
    },
    {
        SerialNumber: "0x59363332393115051808",
        DisplayRounding: 1, 
        GlobalOffset: 1828.11, 
        Offset: [-63214.1, 186820.6, 475.1, 8388607.0], 
        Slope: [-0.00120699, 0.00106272, -0.00110287, 0],
        Shelf: "shop-shelf-02",
        ProductID: 2,
        UnitsAtBegin: 0,
        UnitsCurrent: 0
    }
];

var data_products = [
    {
        ProductID: 0,
        ProductName: "Trauben",
        ProductDescription: "Aus dem eigenen Anbau.",
        Picture: "/images/weintraube.jpg",
        Pricing: {GrammsPerUnit: 100, PricePerUnit: 1.49, Type: 0}
    },
    {
        ProductID: 1,
        ProductName: "Apfelmus",
        ProductDescription: "Eigener Anbau.",
        Picture: "/images/apfelmus.jpg",
        Pricing: {GrammsPerUnit: 800, PricePerUnit: 2.49, Type: 1}
    },
    {
        ProductID: 2,
        ProductName: "Birnen",
        ProductDescription: "Aus dem eigenen Anbau.",
        Picture: "/images/pears.jpgg",
        Pricing: {GrammsPerUnit: 1000, PricePerUnit: 2.99, Type: 0}
    }
];
</script>


    <script type="text/javascript">


        function onConnectionLost() {
            console.log("connection lost");
            document.getElementById("status").innerHTML = "Connection Lost";
            connected_flag = 0;
        }
        function onFailure(message) {
            console.log("MQTT Connection Failed");
            connected_flag = 0;
        }
        function onMessageArrived(r_message) {
            out_msg = "Message received " + r_message.payloadString + "<br>";
            out_msg = out_msg + "Message received Topic " + r_message.destinationName;
            console.log("MQTT recv (" + r_message.destinationName + "): ", r_message.payloadString);

<?php
if ($shelfID == 1) {
?>
            if (r_message.destinationName == 'homie/shop-shelf-01/scale0x57383735393215170b03/status') {
                document.getElementById("msgproduct1").innerHTML = out_msg;
            }
            if (r_message.destinationName == 'homie/shop-shelf-01/scale0x57383735393215170b03/withdrawal') {
                document.getElementById("msgmass1").innerHTML = out_msg;
            }
            <?php
}
if ($shelfID == 2) { ?>
            if (r_message.destinationName == 'homie/shop-shelf-02/scale0x59363332393115051808/status') {
                document.getElementById("msgproduct1").innerHTML = out_msg;
            }
            if (r_message.destinationName == 'homie/shop-shelf-02/scale0x59363332393115171b11/status') {
                document.getElementById("msgproduct2").innerHTML = out_msg;
            }

            if (r_message.destinationName == 'homie/shop-shelf-02/scale0x59363332393115051808/withdrawal') {
                document.getElementById("msgmass1").innerHTML = out_msg;
            }
            if (r_message.destinationName == 'homie/shop-shelf-02/scale0x59363332393115171b11/withdrawal') {
                document.getElementById("msgmass2").innerHTML = out_msg;
            }

            <?php
}
if ($shelfID == 3) { ?>
            if (r_message.destinationName == 'homie/shop-shelf-02/scale0x59363332393115051808/status') {
                document.getElementById("msgproduct1").innerHTML = out_msg;
            }
            if (r_message.destinationName == 'homie/shop-shelf-02/scale0x59363332393115171b11/status') {
                document.getElementById("msgproduct2").innerHTML = out_msg;
            }

            if (r_message.destinationName == 'homie/shop-shelf-02/scale0x59363332393115051808/withdrawal') {
                document.getElementById("msgmass1").innerHTML = out_msg;
            }
            if (r_message.destinationName == 'homie/shop-shelf-02/scale0x59363332393115171b11/withdrawal') {
                document.getElementById("msgmass2").innerHTML = out_msg;
            }

            if (r_message.destinationName == 'homie/shop-shelf-01/scale0x57383735393215170b03/status') {
                document.getElementById("msgproduct3").innerHTML = out_msg;
            }
            if (r_message.destinationName == 'homie/shop-shelf-01/scale0x57383735393215170b03/withdrawal') {
                document.getElementById("msgmass3").innerHTML = out_msg;
            }

<?php
}
?>

        }

        function onConnected(recon, url) {
            console.log(" in onConnected " + reconn);
        }

        function onConnect() {
            console.log("Connected to " + host + ":" + port);
            connected_flag = 1
            document.getElementById("status").innerHTML = "Connected";
            console.log("connected_flag= ", connected_flag);
            mqtt.subscribe("homie/shop-shelf-02/+/#");
            mqtt.subscribe("homie/shop-shelf-01/+/#");
            //message = new Paho.MQTT.Message("Hello World");
            //message.destinationName = "sensor1";
            //mqtt.send(message);
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

        function send_message() {
            if (connected_flag == 0) {
                out_msg = "<b>Not Connected so can't send</b>"
                console.log(out_msg);
                return false;
            }
            var msg = 'test data';
            var topic = 'test topic';
            message = new Paho.MQTT.Message(msg);
            message.destinationName = topic;
            mqtt.send(message);
            return false;
        }

    </script>

</head>

<body>
    <h1>Shelf</h1>

    <table style="width: 100%;" border="0">
        <tbody>
            <tr>
                <td style="vertical-align: top; width: 33%;">
                    <p>Produkt 1</p>
                    <p id="msgproduct1"></p>
                    <p id="msgmass1"></p>
                    
  <p><b><div id="product1_ProductName"></div></b></p>
  <p><div id="product1_ProductDescription"></div></p>
  <p>anfänglich vorhanden: <div id="product1_UnitsAtBegin"></div> Stk</p>
  <p>Rest: <div id="product1_UnitsCurrent"></div> Stk</p>
  <p>entnommen: <div id="product1_UnitsWithdrawal"></div> Stk</p>
  <p>Einheitspreis: <div id="product1_UnitPrice"></div> €/ Stk</p>
  <p>Preis: <div id="product1_price"></div> €</p>
  <img src="" id="product1_img">

                </td>
                <td style="vertical-align: top; width: 33%;">
                    <p>Produkt 2</p>
                    <p id="msgproduct2"></p>
                    <p id="msgmass2"></p>
                </td>
                <td style="vertical-align: top; width: 33%;">
                    <p>Produkt 3</p>
                    <p id="msgproduct3"></p>
                    <p id="msgmass3"></p>
                </td>
            </tr>
        </tbody>
    </table>

    <script>
        var connected_flag = 0;
        var host = "192.168.10.28"; //shop-master
        var port = 8123;
        console.log("Set up the MQTT client (clientshelf<?php echo $shelfID;?>) to connect to " + host + ":" + port);
        var mqtt = new Paho.MQTT.Client(host, port, "clientshelf<?php echo $shelfID;?>");
        mqtt.onConnectionLost = onConnectionLost;
        mqtt.onMessageArrived = onMessageArrived;
        mqtt.onConnected = onConnected;

        var reconnectTimeout = 1000;

    </script>

    <div id="status">Connection Status: Not Connected</div>
    </div>


    <script>
        MQTTconnect();
        
        setInterval(function () { if (connected_flag == 0) MQTTconnect() }, 5 * 1000);
    </script>

    <script>
var my_index = 0;

var item = data_scales[my_index];
var LU_index = -1;
data_products.forEach(function(item_LU, index_LU, array) {
    if (item.ProductID == item_LU.ProductID) {
        LU_index = index_LU;
    }
});

var response;
if (LU_index >= 0) { //Produkt in Tabelle gefunden
    var my_price = 0;
    if (data_products[LU_index].Pricing.Type === 0) { //Gewichtabrechnung
        my_price = (item.UnitsAtBegin-item.UnitsCurrent) / data_products[LU_index].Pricing.GrammsPerUnit * data_products[LU_index].Pricing.PricePerUnit;
    }
    if (data_products[LU_index].Pricing.Type == 1) { //Stückzahl Abrechnung
        my_price = (item.UnitsAtBegin-item.UnitsCurrent) * data_products[LU_index].Pricing.PricePerUnit;
    }
    if (my_price<0) my_price = 0;
    //Round to nearest cent
    my_price = Math.round(my_price*100)/100;

    response = 
            {
            ProductName:data_products[LU_index].ProductName,
            ProductDescription:data_products[LU_index].ProductDescription,
            Picture:data_products[LU_index].Picture,
            UnitsAtBegin:item.UnitsAtBegin,
            UnitsWithdrawal:item.UnitsAtBegin-item.UnitsCurrent,
            UnitsCurrent:item.UnitsCurrent,
            UnitPrice:data_products[LU_index].Pricing.PricePerUnit,
            GrammsPerUnit:data_products[LU_index].Pricing.GrammsPerUnit,
            PriceType:data_products[LU_index].Pricing.Type,
            Price: my_price
        };
    
    document.getElementById('product1_ProductName').innerHTML = response.ProductName;
    document.getElementById('product1_ProductDescription').innerHTML = response.ProductDescription;
    document.getElementById('product1_UnitsAtBegin').innerHTML = response.UnitsAtBegin;
    //document.getElementById('product1_UnitsCurrent').innerHTML = response.ProductName;
    document.getElementById('product1_UnitsWithdrawal').innerHTML = response.UnitsWithdrawal;
    document.getElementById('product1_UnitPrice').innerHTML = response.UnitPrice;
    document.getElementById('product1_price').innerHTML = response.Price;
    document.getElementById('product1_img').src = response.Picture;
}

console.log(response);

</script>

</body>

</html>
