on safeText(valueText)
	if valueText is missing value then
		return ""
	end if
	try
		return valueText as text
	on error
		return ""
	end try
end safeText

on run
	try
		tell application "System Events"
			if not (exists process "Codex") then
				error "Codex is not running."
			end if

			tell process "Codex"
				set frontmost to true
				delay 0.2

				set reportLines to {"PROCESS" & tab & "Codex"}
				try
					copy ("WINDOW" & tab & my safeText(name of front window)) to end of reportLines
				end try

				set inspectedCount to 0
				repeat with uiElement in (entire contents of front window)
					set roleDescriptionText to ""
					set nameText to ""
					set descriptionText to ""
					try
						set roleDescriptionText to my safeText(role description of uiElement)
					end try
					try
						set nameText to my safeText(name of uiElement)
					end try
					try
						set descriptionText to my safeText(value of attribute "AXDescription" of uiElement)
					end try
					if roleDescriptionText is not "" then
						set inspectedCount to inspectedCount + 1
						if inspectedCount is less than or equal to 80 then
							copy ("ELEMENT" & tab & "name=" & nameText & tab & "ax_description=" & descriptionText & tab & "role_description=" & roleDescriptionText) to end of reportLines
						end if
					end if
					if roleDescriptionText is "button" then
						set helpText to ""
						try
							set helpText to my safeText(help of uiElement)
						end try
						copy ("BUTTON" & tab & "name=" & nameText & tab & "ax_description=" & descriptionText & tab & "role_description=" & roleDescriptionText & tab & "help=" & helpText) to end of reportLines
					end if
				end repeat

				set AppleScript's text item delimiters to linefeed
				set reportText to reportLines as string
				set AppleScript's text item delimiters to ""
				return reportText
			end tell
		end tell
	on error errMsg
		return "ERROR" & tab & errMsg
	end try
end run
