<?php
    include "../qr/qr/lib/full/qrlib.php";
 
    $errorCorrectionLevel = 'M';
    if (isset($_GET['level']) && in_array($_GET['level'], array('L','M','Q','H')))
        $errorCorrectionLevel = $_GET['level'];
 
    $matrixPointSize = 4;
    if (isset($_GET['size']))
        $matrixPointSize = min(max((int)$_GET['size'], 1), 10);

    $textData = "no data";
 
    if (isset($_GET['t']) && (trim($_GET['t']) != '')) {
        $textData = $_GET['t'];
    }
    
//    print($textData); 
    QRcode::png($textData, false, $errorCorrectionLevel, $matrixPointSize, 4); // Die letzte 4 ist die Dicke des weißen Rahmens
?>
