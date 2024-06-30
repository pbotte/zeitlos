<?php
$str = "";
switch ($_GET['hostname']) {
  case 'shop-display01':
    $str = "basket.php?shelfid=1";
    break;
  case 'shop-display02':
    $str = "basket.php?shelfid=2";
    break;
  case 'shop-display03':
    $str = "basket.php?shelfid=3";
    break;
  case 'shop-display04':
    $str = "basket.php?shelfid=4";
    break;
  case 'shop-door':
    $str = "door.php";
    break;
  case 'shop-touch':
    $str = "buttons.php";
    break;

}
if (strlen($str)>0) {
  header("Location: http://192.168.10.10/".$str);
}
?>
<html>
  <head>
    <title>Overview</title>
  </head>
<body>
  <h1>Shop pages overview</h1>
  <p>hostname via GET: <?php echo $_GET['hostname']; ?></p>

  <p>Weiter zu: <a href="./door.php?debug=true">door.php</a></p>
  <p>Weiter zu: <a href="./basket.php?debug=true">basket.php</a></p>
  <p>Weiter zu: <a href="./buttons.php?debug=true">buttons.php</a></p>
  <p>Weiter zu: <a href="./invoices.php">Rechungen</a></p>
  <p>Weiter zu: <a href="./invoices3.php">Rechungen mit allen Details</a> (online auch unter <a href="https://www.hemmes24.de/code/invoices3.php?secret=CN87wLAdh1d">https://www.hemmes24.de/code/invoices3.php?secret=CN87wLAdh1d</a>)</p> 

  <p>&nbsp;</p>
  <p><a href="http://192.168.10.2/">Cisco Switch</a>, smartm und pi</p>
  <p><a href="http://192.168.10.10:8080/">phpMyAdmin</a></p>
  <p><a href="http://192.168.10.10:1880/ui">nodered</a></p>
  <p><a href="https://www.hemmes24.de">hemmes24.de</p>
  <p><a href="http://192.168.10.10/qrscanner-debug/">Last picture from qrscanner</a> (start with <pre>qr-scanner.py --save-last-debug-picture</pre> 
and run some copy process like <pre>cd ~/zeitlos/software/www/qrscanner-debug && ./retrieve.sh</pre>)
</body>
