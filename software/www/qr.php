<?php
    include "qr/lib/full/qrlib.php";
 
    $errorCorrectionLevel = 'M';
    if (isset($_GET['level']) && in_array($_GET['level'], array('L','M','Q','H')))
        $errorCorrectionLevel = $_GET['level'];
 
    $matrixPointSize = 4;
    if (isset($_GET['size']))
        $matrixPointSize = min(max((int)$_GET['size'], 1), 10);

    $password = "l28RW4tgGGcslcPzVmt2PsG83nM9XnwgTc98F9phTg7lz9vQnWN4ZMm4MdDvWTCCtgbTJrZTqtLrzSfxMfsXcp9vWPqGwgMjVGqzlcGnhxcs2P4TPCTPlMx9N96gdBt3vmL6Kxms5BmNkLJ5W378LCcdzG37BPNP9KBDFcW9VhffTl5b4gmmpb8MvZ6RljHxzLhmDnjq9BLNpW5tpz4F5jwXvdGLnX4kdzBprhZpPJPxM9b2qzFbqQ3jKtkcWPhp";
    

    /**
 * Return a number only hash
 * https://stackoverflow.com/a/23679870/175071
 * @param $str
 * @param null $len
 * @return number
 */
function numHash($str, $len=null)
{
    $binhash = md5($str, true);
    $numhash = unpack('N2', $binhash);
    $hash = $numhash[1] . $numhash[2];
    if($len && is_int($len)) {
        $hash = substr($hash, 0, $len);
    }
//    return $hash;
    $hash = "";
    $h = md5($str);
    for ($i=0;$i<10;$i++) {
        $hash .= strval(hexdec( substr($h, $i*2+0, 2) ));
        //print($hash."<br>");
    }
    return $hash;
}

    $t = time();
    $h = hash('sha256', $password.$t, false);
    $h = hash('crc32', $password.$t, false);
    $h = hash('md5', $password.$t, false);
    $h = strtoupper($h);

    $data = array("U"=>11, "H"=>$h);
//    $data = array($h);
    $data = array("U"=>11, "H"=>$h);
    $textData = json_encode($data);
    $textData = "11/".$h;
    $textData = "000011".numHash($password.$t);
    $textData = "000011".substr($h,0,12);
 
    if (isset($_GET['text']) && (trim($_GET['text']) != '')) {
        $textData = $_GET['text'];
    }
//print($textData); 
    QRcode::png($textData, false, $errorCorrectionLevel, $matrixPointSize, 0); // Die letzte 0 ist die Dicke des weißen Rahmens
?>

