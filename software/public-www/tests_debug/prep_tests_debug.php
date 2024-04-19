<?php
// This is what PHP functions return:
// gzencode() == gzip
// gzcompress() == zlib (aka. HTTP deflate) equal to python: zlib.compress(data_str.encode(), level=9, wbits=15)
// gzdeflate()  == *raw* deflate encoding


// -----

// hash("crc32b") in php equals the standard crc32 function (for javascript)
// see: https://www.php.net/manual/en/function.crc32.php

$SECRETSTR= "dkf73ngksaubsidab";


//Load data from user via URL
$entered_check_str = "";
if (array_key_exists("c", $_GET)) {
  $entered_check_str = $_GET["c"];
}
$data_str = "";
if (array_key_exists("d", $_GET)) {
  $data_str = $_GET['d'];
  $data_str = str_replace("\r","",$data_str);
  $data_str = str_replace("\n","\\n",$data_str);
}

//Check whether check is okay:
$check_ok = false;
$correct_check_str = "";
if (array_key_exists("d", $_GET)) {
  $str_to_check = $SECRETSTR.$data_str;
  $correct_check_str = hash('crc32b', $str_to_check, false);

  if ($correct_check_str == $entered_check_str) $check_ok = true;
}


//Start decoding
//alt, nur php
//$data_str_encoded = rtrim(strtr(base64_encode(gzdeflate($data_str, 9)), '+/', '-_'), '=');
//neu, php und python
$data_str_encoded = rtrim(strtr(base64_encode(gzcompress($data_str, 9)), '+/', '-_'), '=');

$str_to_check = $SECRETSTR.$data_str_encoded;
$correct_check_str = hash('crc32b', $str_to_check, false);

?>

<!DOCTYPE html>
<html>
<head>
	<title>Large Text Form</title>
	<script src="https://cdn.jsdelivr.net/pako/1.0.3/pako.min.js"></script>
	<script>
		//From https://stackoverflow.com/questions/18638900/javascript-crc32
		var makeCRCTable = function(){
		var c;
		var crcTable = [];
		for(var n =0; n < 256; n++){
			c = n;
			for(var k =0; k < 8; k++){
				c = ((c&1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1));
			}
			crcTable[n] = c;
		}
		return crcTable;
	}

	var crc32 = function(str) {
		var crcTable = window.crcTable || (window.crcTable = makeCRCTable());
		var crc = 0 ^ (-1);

		for (var i = 0; i < str.length; i++ ) {
			crc = (crc >>> 8) ^ crcTable[(crc ^ str.charCodeAt(i)) & 0xFF];
		}

		return (crc ^ (-1)) >>> 0;
	};

	</script>
</head>
<body>
	<p>Jetzt das Python und PHP compatible</p>
	<pre>
<?php
//Start decoding
$c1 = gzcompress($data_str, 9);
$c2 = base64_encode($c1);
echo "$c2\n";
$c3 = strtr($c2, '+/', '-_');
echo "$c3\n";
$c4 = rtrim($c3, '=');
echo "$c4\n";

$c4 = gzuncompress(base64_decode($c2));
echo "$c4\n";

?>
	</pre>
	<hr>


	<form method="GET" action="prep.php">
		<label for="large_text">Large Text:</label>
		<br>
		d: <textarea name="d" id="myinput" rows="10" cols="50"><?= $data_str?></textarea>
		<br>
		check: <input name="check" value="<?= $correct_check_str?>">
		<br>
		<input type="submit" value="Submit">
	</form>
	
	<p><a href="./invoice2.php?d=<?= $data_str_encoded?>&c=<?= $correct_check_str?>">zum PDF (index.php)</a></p>
	<p><img src="/code/qr.php?t=<? echo("https://www.hemmes24.de/code/invoice2.php?d%3D".$data_str_encoded."%26c%3D".$correct_check_str)?>"></p>
	
	<p><br></p>
	Example: <textarea rows="10" cols="50">{"d":{"p":[["Produkt 1",1,42.5,0],["Produkt 2",5,5.2,1],["Birnen",3,2.2,2],["Produkt 3",3,10,2]],"c":"add card text","t": 1683378472}}</textarea>

	<hr>
	<p><img id="qrpic"></p>
	<iframe id="myIframe" width="600" height="1000"></iframe>

	<hr>
	<pre><script>
function encodeDataString(data_str) {
	data_str = document.getElementById('myinput').value;

  var c1 = pako.deflate(data_str, { level: 9 , windowBits:15});

  var base64EncodedData = btoa(String.fromCharCode.apply(null, c1))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');

  document.write(base64EncodedData);

  var SECRETSTR= "blablablaskfjshfushdfisuh5487wzfisaubsidab";
  var str_to_check = SECRETSTR + base64EncodedData;
  var correct_check_str = crc32(str_to_check).toString(16);
  correct_check_str = correct_check_str.padStart(8, "0"); //put leading "0" if too short
  document.write("\n"+correct_check_str.toString(16));

  
  const iframe = document.getElementById('myIframe');
	iframe.src = 'https://www.hemmes24.de/code/invoice2.php?d='+base64EncodedData+'&c='+correct_check_str+'&out=html';

	const qrpic = document.getElementById('qrpic');
	qrpic.src="/code/qr.php?t=https://www.hemmes24.de/code/invoice2.php?d%3D"+base64EncodedData+"%26c%3D"+correct_check_str;

}

// Example usage:
var data = "hallo";
encodeDataString(data);
</script>
</pre>


</body>
</html>
