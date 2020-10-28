<?php
$str = "";
switch ($_GET['hostname']) {
  case 'shop-door':
        $str = "door.html";
        break;
  case 'shop-shelf-01':
	$str = "shelf.php?shelfid=1";
	break;
  case 'shop-shelf-02':
        $str = "shelf.php?shelfid=2";
        break;

}
//header("Location: http://shop-master/".$str);
header("Location: http://192.168.10.28/".$str);
?>
<h1>Shop</h1>
<p><?php echo $_GET['hostname']; ?></p>
<p><hr></p>
<p><?php phpinfo(); ?></p>
