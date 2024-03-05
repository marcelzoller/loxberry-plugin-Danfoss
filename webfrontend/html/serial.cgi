#!/usr/bin/perl

# Einbinden von Module
use CGI;
use LoxBerry::System;
use LoxBerry::Web;
use LoxBerry::Log;
use LoxBerry::JSON;
use IO::Socket::INET;
use LWP::Simple;
#use Net::Ping;
#use strict;
#use warnings;
use Device::SerialPort;

my $danfoss_debug = 0;
my $danfoss_debug_stuffing = 0;
my $danfoss_sleep = 1;

my $str_Gesamt = 0;
my $str_Aktuell = 0;
my $str_Tagesenergie = 0;
my $str_String1 = 0;
my $str_String2 = 0;
my $str_Status = 0;
my $str_Eventcode = 0;


# Prozedure um die DANFOSS 4 Bytes zu filtern
sub bytestuffing {
   my ($datastring, $debug) = @_;
   my $offset = 0;
   my $offset_block1 = 0;
   my $offset_block2 = 0;
   my $offset_block3 = 0;
   my $offset_block4 = 0;
   if (substr($datastring, 4, 2) ne "03") {
       $offset = 2;
   }
   if (substr($datastring, 30 + $offset, 2) eq "7d") {
       if (substr($datastring, 32 + $offset, 2) eq "5e") {
           $block1 = "7e";
           $offset_block2 = 2;
       }
       if (substr($datastring, 32 + $offset, 2) eq "5d") {
           $block1 = "7d";
           $offset_block2 = 2;
       }
   } else {
       $block1 = substr($datastring, 30 + $offset, 2);
   }
   if (substr($datastring, 32 + $offset + $offset_block2, 2) eq "7d") {
       if (substr($datastring, 34 + $offset + $offset_block2, 2) eq "5e") {
           $block2 = "7e";
           $offset_block3 = 2;
       }
       if (substr($datastring, 34 + $offset + $offset_block2, 2) eq "5d") {
           $block2 = "7d";
           $offset_block3 = 2;
       }
   } else {
       $block2 = substr($datastring, 32 + $offset + $offset_block2, 2);
   }
   if (substr($datastring, 34 + $offset + $offset_block2 + $offset_block3, 2) eq "7d") {
       if (substr($datastring, 36 + $offset + $offset_block2 + $offset_block3, 2) eq "5e") {
           $block3 = "7e";
           $offset_block4 = 2;
       }
       if (substr($datastring, 36 + $offset + $offset_block2 + $offset_block3, 2) eq "5d") {
           $block3 = "7d";
           $offset_block4 = 2;
       }
   } else {
       $block3 = substr($datastring, 34 + $offset + $offset_block2 + $offset_block3, 2);
   }
   if (substr($datastring, 36 + $offset + $offset_block2 + $offset_block3 + $offset_block4, 2) eq "7d") {
       if (substr($datastring, 38 + $offset + $offset_block2 + $offset_block3 + $offset_block4, 2) eq "5e") {
           $block4 = "7e";
       }
       if (substr($datastring, 38 + $offset + $offset_block2 + $offset_block3 + $offset_block4, 2) eq "5d") {
           $block4 = "7d";
       }
   } else {
       $block4 = substr($datastring, 36 + $offset + $offset_block2 + $offset_block3 + $offset_block4, 2);
   }
   my $data = $block4 . $block3 . $block2 . $block1;
   if ($debug) {
       print $datastring . ":" . substr($datastring, 4, 2) . ": " . $data . "\n";
   }
   my $result = $data;
   return $result;
}

# Ersetzen Sie '/dev/ttyUSB0' mit dem korrekten Gerätedateinamen Ihres USB-Seriell-Adapters
$USBPort = "/dev/ttyUSB0"; 
my $port = Device::SerialPort->new($USBPort) || die "Can't Open $USBPorts: $!";

# Konfigurieren Sie die Serial-Port-Einstellungen
$port->baudrate(19200);
$port->databits(8);
$port->parity("none");
$port->stopbits(1);

# Gesamt Wh
# 7e ff 03 ee fe 11 04 0A 01 C8 08 d0 01 02 87 00 00 00 00 b0 ab 7e
my $MESSAGE_Gesamt	= "7eff03eefe11040A01C808d001028700000000b0ab7e";

# Tagesenergie Wh
# 7e ff 03 ee fe 11 04 0A 01 C8 08 d0 02 4a 87 00 00 00 00 57 20 7e  
my $MESSAGE_Tagesenergie	= "7eff03eefe11040A01C808d0024a870000000057207e";

# Aktuell Watt
# 7e ff 03 ee fe 11 04 0A 01 C8 08 d0 02 46 87 00 00 00 00 a3 11 7e
my $MESSAGE_aktuell	= "7eff03eefe11040A01C808d002468700000000a3117e";

# Now String 1 Watt
# 7e ff 03 ee fe 11 04 0A 01 C8 08 d0 02 32 86 00 00 00 00 4a cf 7
my $MESSAGE_String1	= "7eff03eefe11040A01C808d0023286000000004acf7e";

# Now String 2 Watt
# 7e ff 03 ee fe 11 04 0A 01 C8 08 d0 02 33 86 00 00 00 00 61 cb 7e
my $MESSAGE_String2	= "7eff03eefe11040A01C808d00233860000000061cb7e";

# Now Phase 1 Watt => not work
# 7e ff 03 ee fe 11 04 0A 01 C8 08 d0 02 42 87 00 00 00 00 0f 10 7e

# Now Phase 2 Watt => not work
# 7e ff 03 ee fe 11 04 0A 01 C8 08 d0 02 46 87 00 00 00 00 04 52 7e

# Now Phase 3 Watt => not work
# 7e ff 03 ee fe 11 04 0A 01 C8 08 d0 02 46 87 00 00 00 00 f5 19 7e

# Status
# 7e ff 03 ee fe 11 04 0A 01 C8 08 d0 0a 02 86 00 00 00 00 76 d6 7e
my $MESSAGE_Status	= "7eff03eefe11040A01C808d00a02860000000076d67e";

# Eventcode
# 7e ff 03 ee fe 11 04 0A 01 C8 08 d0 0a 28 86 00 00 00 00 18 7a 7e		
my $MESSAGE_Eventcode= "7eff03eefe11040A01C808d00a288600000000187a7e";	

# ping Danfoss 1 1 4
# 7e ff 03 ee fe 11 04 00 15 cc 67 7e
my $MESSAGE_Ping = "7eff03eefe11040015cc677e";	


# Umwandeln des Hex-Textes in binäre Daten
my $binary_data = pack('H*', $MESSAGE_Ping);

# Schreiben Sie die binären Daten zum Port
$port->write($binary_data);

# Warten auf die Antwort
sleep($danfoss_sleep); # Gegebenenfalls anpassen


# Schleife, um Daten kontinuierlich zu empfangen
my $data_Ping="";
my ($count, $received_data) = $port->read(30); # Lesen von bis zu 30 Zeichen
if ($count > 0) {
	# Konvertieren der empfangenen Binärdaten in Hex-Text
	 $data_Ping = unpack('H*', $received_data);
	#print "Empfangene Daten (Hex): $data_Ping\n";
}

$data_Ping = substr($data_Ping, 4, 24);
#print("Danfoss PING1: " . $data_Ping . "\n");
if (substr($data_Ping, 2, 2) eq "03") { # Manchmal, kommt eine längere Antwort zurück.
    $data_Ping = substr($data_Ping, 2, 24);
    #print("Danfos PING2: " . $data_Ping . "\n");
}
if ($data_Ping eq "031104eefe00957cf77e") {
	
	if($danfoss_debug) {print "Danfoss WR ist online!\n";}
	
	# Abfrage Gessamtenergie kWh
	my $binary_data = pack('H*', $MESSAGE_Gesamt);
	$port->write($binary_data);
	sleep($danfoss_sleep);
	my ($count, $received_data) = $port->read(30); 
	if ($count > 0) {
		 $data_Gesamt = unpack('H*', $received_data);
		#print "Empfangene Daten (Hex): $data_Gesamt\n";
		#print "Empfangene Daten: $received_data\n"; 
		
		$str_Gesamt = bytestuffing($data_Gesamt, $danfoss_debug_stuffing);
		#my $str_Gesam = $data_Gesamt;
		$str_Gesamt = hex($str_Gesamt)/1000;
		
		if($danfoss_debug) {print("Danfoss Gesamtenergie: $str_Gesamt kWh\n");}
	}
	
	# Abfrage Danfoss Aktuell Watt
	my $binary_data = pack('H*', $MESSAGE_aktuell);
	$port->write($binary_data);
	sleep($danfoss_sleep);
	my ($count, $received_data) = $port->read(30); 
	if ($count > 0) {
		$data_Aktuell = unpack('H*', $received_data);
		$str_Aktuell = bytestuffing($data_Aktuell, $danfoss_debug_stuffing);
		$str_Aktuell = hex($str_Aktuell) ;
		if($danfoss_debug) {print("Danfoss Aktuell $str_Aktuell Watt\n");}
	}
	
	# Abfrage Danfoss Tagesenergie kWh
	my $binary_data = pack('H*', $MESSAGE_Tagesenergie);
	$port->write($binary_data);
	sleep($danfoss_sleep);
	my ($count, $received_data) = $port->read(30); 
	if ($count > 0) {
		$data_Tagesenergie = unpack('H*', $received_data); 
		$str_Tagesenergie = bytestuffing($data_Tagesenergie, $danfoss_debug_stuffing);
		$str_Tagesenergie = hex($str_Tagesenergie)/1000;
		if($danfoss_debug) {print("Danfoss Tagesenegie $str_Tagesenergie kWh\n");}
	}
	
	# Abfrage Danfoss String 1 Watt
	my $binary_data = pack('H*', $MESSAGE_String1);
	$port->write($binary_data);
	sleep($danfoss_sleep);
	my ($count, $received_data) = $port->read(30); 
	if ($count > 0) {
		$data_String = unpack('H*', $received_data); 
		$str_String1 = bytestuffing($data_String, $danfoss_debug_stuffing);
		$str_String1 = hex($str_String1);
		if($danfoss_debug) {print("Danfoss String 1 $str_String1 Watt\n");}
	}
		
	# Abfrage Danfoss String 2 Watt
	my $binary_data = pack('H*', $MESSAGE_String2);
	$port->write($binary_data);
	sleep($danfoss_sleep);
	my ($count, $received_data) = $port->read(30); 
	if ($count > 0) {
		$data_String = unpack('H*', $received_data); 
		$str_String2 = bytestuffing($data_String, $danfoss_debug_stuffing);
		$str_String2 = hex($str_String2);
		if($danfoss_debug) {print("Danfoss String 2 $str_String2 Watt\n");}
	}
			
	# Abfrage Danfoss Status
	my $binary_data = pack('H*', $MESSAGE_Status);
	$port->write($binary_data);
	sleep($danfoss_sleep);
	my ($count, $received_data) = $port->read(30); 
	if ($count > 0) {
		$data_Status = unpack('H*', $received_data); 
		$str_Status = bytestuffing($data_Status, $danfoss_debug_stuffing);
		$str_Status = hex($str_Status);
		if($danfoss_debug) {print("Danfoss Status $str_Status \n");}
	}
				
	# Abfrage Danfoss Status
	my $binary_data = pack('H*', $MESSAGE_Eventcode);
	$port->write($binary_data);
	sleep($danfoss_sleep);
	my ($count, $received_data) = $port->read(30); 
	if ($count > 0) {
		$data_Event = unpack('H*', $received_data); 
		$str_Eventcode = bytestuffing($data_Event, $danfoss_debug_stuffing);
		$str_Eventcode = hex($str_Eventcode);
		if($danfoss_debug) {print("Danfoss Eventcode $str_Eventcode \n");}
	}
}
print("Danfoss WR ist online!\n");
print("Danfoss Gesamtenergie: $str_Gesamt kWh\n");
print("Danfoss Aktuell $str_Aktuell Watt\n");
print("Danfoss Tagesenegie $str_Tagesenergie kWh\n");
print("Danfoss String 1 $str_String1 Watt\n");
print("Danfoss String 2 $str_String2 Watt\n");
print("Danfoss Status $str_Status \n");
print("Danfoss Eventcode $str_Eventcode \n");

# Schließen Sie den Port
$port->close;

