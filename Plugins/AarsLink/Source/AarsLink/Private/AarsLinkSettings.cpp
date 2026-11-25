#include "AarsLinkSettings.h"

UAarsLinkSettings::UAarsLinkSettings()
{
	DefaultTanker.IasKt = 250.0;
	DefaultTanker.AltFt = 25000.0;
	DefaultTanker.BankDeg = 0.0;
	DefaultTanker.PitchDeg = 2.0;
	DefaultTanker.HeadingDeg = 90.0;
	DefaultTanker.Ap = EAarsAutopilot::Cmd;
}
