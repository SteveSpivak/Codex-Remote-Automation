on replace_text(find_text, replace_text, source_text)
	set AppleScript's text item delimiters to find_text
	set text_items to every text item of source_text
	set AppleScript's text item delimiters to replace_text
	set joined_text to text_items as text
	set AppleScript's text item delimiters to ""
	return joined_text
end replace_text

on json_escape(source_text)
	set escaped_text to my replace_text("\\", "\\\\", source_text)
	set escaped_text to my replace_text("\"", "\\\"", escaped_text)
	set escaped_text to my replace_text(return, "\\n", escaped_text)
	set escaped_text to my replace_text(linefeed, "\\n", escaped_text)
	return escaped_text
end json_escape

on run argv
	if (count of argv) < 2 then error "Usage: cra_send_imessage.applescript <handle> <message>"
	set handle_value to item 1 of argv
	set message_text to item 2 of argv
	
	tell application "Messages"
		set target_service to 1st service whose service type = iMessage
		set target_buddy to buddy handle_value of target_service
		send message_text to target_buddy
	end tell
	
	return "{\"status\":\"ok\",\"handle\":\"" & my json_escape(handle_value) & "\"}"
end run
