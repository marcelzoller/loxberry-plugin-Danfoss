#!/usr/bin/perl

# Einbinden von Module
use CGI;
use LoxBerry::System;
use LoxBerry::Web;
use LoxBerry::Log;
use LoxBerry::JSON;
use IO::Socket::INET;
use LWP::Simple;
use Net::Ping;
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


print "Content-type: text/html\n\n";

# Konfig auslesen
my %pcfg;
my %miniservers;
tie %pcfg, "Config::Simple", "$lbpconfigdir/pluginconfig.cfg";
$UDP_Port = %pcfg{'MAIN.UDP_Port'};
#$UDP_Send_Enable = %pcfg{'MAIN.UDP_Send_Enable'};
$HTTP_TEXT_Send_Enable = %pcfg{'MAIN.HTTP_TEXT_Send_Enable'};
$MINISERVER = %pcfg{'MAIN.MINISERVER'};
%miniservers = LoxBerry::System::get_miniservers();


# Miniserver konfig auslesen
#print "\n".substr($MINISERVER, 10, length($MINISERVER))."\n";
$i = substr($MINISERVER, 10, length($MINISERVER));
$LOX_Name = $miniservers{$i}{Name};
$LOX_IP = $miniservers{$i}{IPAddress};
$LOX_User = $miniservers{$i}{Admin};
$LOX_PW = $miniservers{$i}{Pass};

print "Miniserver\@".$LOX_Name."<br>";
#print $LOX_IP."<br>";
#print $LOX_User."<br>";
#print $LOX_PW."<br>";

# Mit dieser Konstruktion lesen wir uns alle POST-Parameter in den Namespace R.
my $cgi = CGI->new;
$cgi->import_names('R');
# Ab jetzt kann beispielsweise ein POST-Parameter 'form' ausgelesen werden mit $R::form.


# POST request
$VZug_IP = $R::ip;
# $VZug_IP = "172.16.200.105";



# Create my logging object
my $log = LoxBerry::Log->new ( 
	name => 'cronjob',
	filename => "$lbplogdir/danfoss.log",
	append => 1
	);
LOGSTART "Kostal cronjob start";

# UDP-Port Erstellen für Loxone
my $sock = new IO::Socket::INET(PeerAddr => $LOX_IP,
                PeerPort => $UDP_Port,
                Proto => 'udp', Timeout => 1) or die('Error opening socket.');
			

# Loxone HA-Miniserver by Marcel Zoller	
if($LOX_Name eq "lxZoller1"){
	# Loxone Minisever ping test
	LOGOK " Loxone Zoller HA-Miniserver";
	#$LOX_IP="172.16.200.7"; #Testvariable
	#$LOX_IP='172.16.200.6'; #Testvariable
	$p = Net::Ping->new();
	$p->port_number("80");
	if ($p->ping($LOX_IP,2)) {
				LOGOK "Ping Loxone: Miniserver1 is online.";
				LOGOK "Ping Loxone: $p->ping($LOX_IP)";
				$p->close();
			} else{ 
				LOGALERT "Ping Loxone: Miniserver1 not online!";
				LOGDEB "Ping Loxone: $p->ping($LOX_IP)";
				$p->close();
				
				$p = Net::Ping->new();
				$p->port_number("80");
				$LOX_IP = $miniservers{2}{IPAddress};
				$LOX_User = $miniservers{2}{Admin};
				$LOX_PW = $miniservers{2}{Pass};
				#$LOX_IP="172.16.200.6"; #Testvariable
				if ($p->ping($LOX_IP,2)) {
					LOGOK "Ping Loxone: Miniserver2 is online.";
					LOGOK "Ping Loxone: $p->ping($LOX_IP)";
				} else {
					LOGALERT "Ping Loxone: Miniserver2 not online!";
					LOGDEB "Ping Loxone: $p->ping($LOX_IP)";
					#Failback Variablen !!!
					$LOX_IP = $miniservers{1}{IPAddress};
					$LOX_User = $miniservers{1}{Admin};
					$LOX_PW = $miniservers{1}{Pass};	
				} 
			}
		$p->close();			
}

my @vzugIP;
# Alle VZUG IPs aus der Konfig
my $hisIP;	
my $k;


$k = 1;
$dev1ip = %pcfg{"Device$k.IP"};
push @vzugIP, $dev1ip;
#print "$vzugIP[$i]<br>";

LOGDEB "Loxone Name: $LOX_Name";			
# $dev1ip = %pcfg{'Device1.IP'};
if ($VZug_IP ne "") {
	$dev1ip = $VZug_IP;
}

if ($dev1ip ne "") {
	LOGDEB "Danfoss USB Device: $dev1ip";
	
	# Ersetzen Sie '/dev/ttyUSB0' mit dem korrekten Gerätedateinamen Ihres USB-Seriell-Adapters
	#$USBPort = "/dev/ttyUSB0"; 
	$USBPort = $dev1ip;
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
		print "DanfossOnline\@1<br>";
	}
	else {
		print "DanfossOnline\@0<br>";
	}	
	#print("Danfoss WR ist online!\n");
	#print("Danfoss Gesamtenergie: $str_Gesamt kWh\n");
	#print("Danfoss Aktuell $str_Aktuell Watt\n");
	#print("Danfoss Tagesenegie $str_Tagesenergie kWh\n");
	#print("Danfoss String 1 $str_String1 Watt\n");
	#print("Danfoss String 2 $str_String2 Watt\n");
	#print("Danfoss Status $str_Status \n");
	#print("Danfoss Eventcode $str_Eventcode \n");

	# Schließen Sie den Port
	$port->close;


	print "DanfossGesamt\@$str_Gesamt<br>";
	print "DanfossTagesenergie\@$str_Tagesenergie<br>";
	print "DanfossStatus\@$str_Status<br>";
	print "DanfossEventcode\@$str_Eventcode<br>";
	print "DanfossSpannungString1\@$str_String1<br>";
	print "DanfossSpannungString2\@$str_String2<br>";
	print "DanfossSpannungAktuell\@$str_Aktuell<br><br>";



	if ($HTTP_TEXT_Send_Enable == 1) {
		LOGDEB "Loxone IP: $LOX_IP";
		LOGDEB "User: $LOX_User";
		LOGDEB "Password: $LOX_PW";
		# wgetstr = "wget --quiet --output-document=temp http://"+loxuser+":"+loxpw+"@"+loxip+"/dev/sps/io/PV_Danfoss_aktuell/" + str(ProgrammStr) 
		$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/PV_Danfoss_aktuell/$str_Aktuell");
		$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/PV_Danfoss_gesamtenergie/$str_Gesamt");
		$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/PV_Danfoss_Status$str_Status");
		$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/PV_Danfoss_Eventcode/$str_Eventcode");
		$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/PV_Danfoss_String1/$str_String1");
		$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/PV_Danfoss_String2/$str_String2");
		$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/PV_Danfoss_tagesenergie/$str_Tagesenergie");


		LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/PV_Danfoss_aktuell/$str_Aktuell";
		LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/PV_Danfoss_gesamtenergie/$str_Gesamt";
		LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/PV_Danfoss_Status/$str_Status";
		LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/PV_Danfoss_Eventcode/$str_Eventcode";
		LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/PV_Danfoss_String1/$str_String1";
		LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/PVPV_Danfoss_String2/$str_String2";
		LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/PV_Danfoss_tagesenergie/$str_Tagesenergie";
	
		}
	else {
		LOGDEB "HTTP_TEXT_Send_Enable: 0";
	}
		
	if ($UDP_Send_Enable == 1) {
		print $sock "PV_Danfoss_aktuell\@$str_Spannung_Aktuell\;";
		LOGDEB "Loxone IP: $LOX_IP";

		LOGDEB "UDP Port: $UDP_Port";
		LOGDEB "UDP Send: PV_Danfoss_aktuell\@$str_Spannung_Aktuell\;";
		
	}
}
# Schließen des Sockets
close($sock);

# We start the log. It will print and store some metadata like time, version numbers
# LOGSTART "Danfoss cronjob start";
  
# Now we really log, ascending from lowest to highest:
# LOGDEB "This is debugging";                 # Loglevel 7
# LOGINF "Infos in your log";                 # Loglevel 6
# LOGOK "Everything is OK";                   # Loglevel 5
# LOGWARN "Hmmm, seems to be a Warning";      # Loglevel 4
# LOGERR "Error, that's not good";            # Loglevel 3
# LOGCRIT "Critical, no fun";                 # Loglevel 2
# LOGALERT "Alert, ring ring!";               # Loglevel 1
# LOGEMERGE "Emergency, for really really hard issues";   # Loglevel 0
  
LOGEND "Operation finished sucessfully.";
