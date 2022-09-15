<?php
$str = "";
switch ($_GET['hostname']) {
  case 'shop-display01':
    $str = "door.php";
    break;
  case 'shop-display02':
    $str = "basket.php";
    break;
  case 'shop-touch01':
    $str = "buttons.php";
    break;
  case 'shop-touch2':
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


</body>
