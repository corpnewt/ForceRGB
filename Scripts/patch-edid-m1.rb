#!/usr/bin/ruby
# Modified version of patch-edid.rb for Apple Silicon (M1/M2/M3) Macs
# Original: https://gist.github.com/adaugherity/7435890

require 'base64'

# On Apple Silicon, we need to use a different approach
data = `ioreg -l -w0`

# Extract EDID data for external displays
edid_matches = data.scan(/"EDID" = <([a-f0-9]+)>/i)
product_matches = data.scan(/"ProductID"=(\d+)/)
vendor_matches = data.scan(/"LegacyManufacturerID"=(\d+)/)
name_matches = data.scan(/"ProductName"="([^"]+)"/)

displays = []
edid_matches.each_with_index do |edid_match, i|
    edid_hex = edid_match[0]
    # Skip if this looks like built-in display EDID (typically much shorter)
    next if edid_hex.length < 200
    
    # Try to find corresponding product info
    if i < product_matches.length && i < vendor_matches.length && i < name_matches.length
        product_id = product_matches[i][0].to_i
        vendor_id = vendor_matches[i][0].to_i
        display_name = name_matches[i][0]
        
        # Skip built-in displays (Apple vendor ID is 0x106b = 4203)
        next if vendor_id == 4203
        
        disp = {
            "edid_hex" => edid_hex,
            "vendorid" => vendor_id,
            "productid" => product_id,
            "name" => display_name
        }
        displays.push(disp)
    end
end

# Process all displays
if displays.length > 1
    puts "Found %d displays!  You should only install the override file for the one which" % displays.length
    puts "is giving you problems.", "\n"
elsif displays.length == 0
    puts "No external display data found!"
    puts "This might be because:"
    puts "1. No external displays are connected"
    puts "2. The display is using a connection type that doesn't expose EDID"
    puts "3. The display EDID is not accessible via this method"
    exit 1
end

displays.each do |disp|
    monitor_name = disp["name"] || "Display"
    
    puts "Found display '#{monitor_name}': vendor ID=#{disp["vendorid"]} (0x%x), product ID=#{disp["productid"]} (0x%x)" %
            [disp["vendorid"], disp["productid"]]
    puts "Raw EDID data:\n#{disp["edid_hex"]}"

    bytes = disp["edid_hex"].scan(/../).map{|x| Integer("0x#{x}")}.flatten

    puts "Setting color support to RGB 4:4:4 only"
    bytes[24] &= ~(0b11000)

    puts "Number of extension blocks: #{bytes[126]}"
    puts "Removing extension block"
    bytes = bytes[0..127]
    bytes[126] = 0

    bytes[127] = (0x100-(bytes[0..126].reduce(:+) % 256)) % 256
    puts
    puts "Recalculated checksum: 0x%x" % bytes[127]
    puts "New EDID:\n#{bytes.map{|b|"%02X"%b}.join}"

    Dir.mkdir("DisplayVendorID-%x" % disp["vendorid"]) rescue nil
    filename = "DisplayVendorID-%x/DisplayProductID-%x" % [disp["vendorid"], disp["productid"]]
    puts "Output file: #{Dir.pwd}/#{filename}"
    
    f = File.open(filename, 'w')
    f.write '<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">'
    f.write "
<dict>
  <key>DisplayProductName</key>
  <string>#{monitor_name} - forced RGB mode (EDID override)</string>
  <key>IODisplayEDID</key>
  <data>#{Base64.encode64(bytes.pack('C*'))}</data>
  <key>DisplayVendorID</key>
  <integer>#{disp["vendorid"]}</integer>
  <key>DisplayProductID</key>
  <integer>#{disp["productid"]}</integer>
</dict>
</plist>"
    f.close
    puts "\n"
end 