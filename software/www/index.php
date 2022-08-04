<?php
$str = "";
switch ($_GET['hostname']) {
  case 'shop-door':
    $str = "door.php";
    break;
  case 'shop-shelf-01':
	  $str = "shelf.php?shelfid=1";
	  break;
  case 'shop-shelf-02':
    $str = "shelf.php?shelfid=2";
    break;

}
if (strlen($str)>0) {
  header("Location: http://192.168.179.150/".$str);
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


</body>