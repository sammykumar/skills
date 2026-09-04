-- Handles claude-resume://<session-uuid> links clicked in the statusline's top
-- border and puts `claude --resume <uuid>` on the clipboard.
--
-- Terminals cannot copy on click: OSC-8 only hands a URI to the OS, so the
-- clipboard step has to happen in a registered scheme handler like this one.

on open location this_URL
	set schemePrefix to "claude-resume://"
	if this_URL does not start with schemePrefix then return

	set sessionID to text ((count of schemePrefix) + 1) thru (count of this_URL) of this_URL
	-- Browsers and some launchers append a trailing slash to authority-only URLs.
	if sessionID ends with "/" then set sessionID to text 1 thru -2 of sessionID
	if sessionID is "" then return

	set resumeCommand to "claude --resume " & sessionID
	set the clipboard to resumeCommand
	display notification resumeCommand with title "Resume command copied"
end open location

-- Launched without a URL (e.g. double-clicked in Finder): say what this is for.
on run
	display notification "Click a session id in the Claude statusline to copy its resume command." with title "Claude Resume Copy"
end run
