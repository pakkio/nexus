// Example osTeleportAgent Script
//
// Set Destination as described below, There are a Few Options depending on Application:
// IN GRID Teleport 
// Destination = "1000,1000"; = Using In-Grid Map XXXX,YYYY coordinates
// Destination = "RegionName"; = Using RegionName
// HyperGrid Teleport (region must be HG Enabled)
// Destination = "TcpIpAddr:Port:RegionName"; = Using the Target/Destination IP Address
// Destination = "DNSname:Port:RegionName"; = Using the Target/Detination DNSname
// Note: RegionName is Optionally Specified to deliver Avatar to specific region in an instance.
// 
// ========================================================================================
// === SET DESTINATION INFO HERE ===
//
string Destination = "NoiLab 2"; // your target destination here (SEE NEXT LINES) Can Be
vector LandingPoint = <432,331,1006>; // X,Y,Z landing point for avatar to arrive at
vector LookAt = <1,1,1>; // which way they look at when arriving
//
default
{
 on_rez(integer start_param)
 {
 llResetScript();
 }
 changed(integer change) // something changed, take action
 {
 if(change & CHANGED_OWNER)
 {
 llResetScript();
 }
 else if (change & 256) // that bit is set during a region restart
 { 
 llResetScript();
 }
 }
 
 state_entry()
 {
 llWhisper(0, "OS Teleportal Active");
 }
 
 touch_start(integer num_detected) 
 {
 key avatar = llDetectedKey(0);
 llInstantMessage(avatar, "Teleporting you to : "+Destination);
 osTeleportAgent(avatar, Destination, LandingPoint, LookAt); 
 }
}
