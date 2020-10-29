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
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN" "http://www.w3.org/TR/html4/frameset.dtd">
<html>
  <frameset cols="*,400" frameborder="1">
    <frame src="shelf-detail.php?shelfid=<?php echo($shelfID); if (strlen($debugClientStrSuffix) >0) {echo '&debug=true';}?>" name="shelf">
    <frame src="basket.php?shelfid=<?php echo($shelfID); if (strlen($debugClientStrSuffix) >0) {echo '&debug=true';}?>" name="basket">
  </frameset>
</html>