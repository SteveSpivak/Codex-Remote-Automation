on run argv
	if (count of argv) is not 3 and (count of argv) is not 4 then
		error "Usage: cra_actuate.applescript <mode> <decision> <action_id> [ax_description]"
	end if

	set modeText to item 1 of argv
	set decisionText to item 2 of argv
	set actionIdText to item 3 of argv
	set selectorDescription to ""
	if (count of argv) is 4 then
		set selectorDescription to item 4 of argv
	end if

	if modeText is not "live" then
		return "status=dry-run decision=" & decisionText & " action_id=" & actionIdText
	end if

	try
		tell application "System Events"
			if not (exists process "Codex") then
				error "Codex is not running."
			end if

			tell process "Codex"
				set frontmost to true
				delay 0.2
				if selectorDescription is "" then
					error "No live selector AXDescription was provided."
				end if

				set matchedButton to missing value
				repeat with uiButton in (every button of entire contents of front window)
					try
						set currentDescription to value of attribute "AXDescription" of uiButton
						if currentDescription is selectorDescription then
							set matchedButton to uiButton
							exit repeat
						end if
					end try
				end repeat

				if matchedButton is missing value then
					error "No button with AXDescription=" & selectorDescription & " was found."
				end if

				click matchedButton
				return "status=clicked decision=" & decisionText & " action_id=" & actionIdText & " ax_description=" & selectorDescription
			end tell
		end tell
	on error errMsg
		error errMsg
	end try
end run
