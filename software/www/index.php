<?php
$str = "";
switch ($_GET['hostname']) {
  case 'shop-display01':
    $str = "door.php";
    break;
  case 'shop-display02':
    $str = "basket.php";
    break;
  case 'shop-touch':
    $str = "buttons.php";
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

  <p>Weiter zu: <a href="./door.php">door.php</a></p>
  <p>Weiter zu: <a href="./basket.php">basket.php</a></p>
  <p>Weiter zu: <a href="./buttons.php">buttons.php</a></p>

  <p>&nbsp;</p>
  <p><a href="http://192.168.10.10:8080/">phpMyAdmin</a></p>
  <p><a href="http://192.168.10.10:1880/ui">nodered</a></p>
  <p><a href="https://www.hemmes24.de">hemmes24.de</p>

</body>
