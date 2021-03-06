# -*- coding: UTF-8 -*-
#settingsDialogs.py
#A part of NonVisual Desktop Access (NVDA)
#Copyright (C) 2006-2017 NV Access Limited, Peter Vágner, Aleksey Sadovoy, Rui Batista, Joseph Lee, Heiko Folkerts, Zahari Yurukov, Leonard de Ruijter, Derek Riemer, Babbage B.V., Davy Kager, Ethan Holliger
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.

import glob
import os
import copy
import re
import wx
from wx.lib import scrolledpanel
import winUser
import logHandler
import installer
from synthDriverHandler import *
import config
import languageHandler
import speech
import gui
from gui import nvdaControls
import globalVars
from logHandler import log
import nvwave
import audioDucking
import speechDictHandler
import appModuleHandler
import queueHandler
import braille
import brailleTables
import brailleInput
import core
import keyboardHandler
import characterProcessing
import guiHelper
try:
	import updateCheck
except RuntimeError:
	updateCheck = None
import inputCore
import nvdaControls

class SettingsDialog(wx.Dialog):
	"""A settings dialog.
	A settings dialog consists of one or more settings controls and OK and Cancel buttons.
	Action may be taken in response to the OK or Cancel buttons.

	To use this dialog:
		* Set L{title} to the title of the dialog.
		* Override L{makeSettings} to populate a given sizer with the settings controls.
		* Optionally, override L{postInit} to perform actions after the dialog is created, such as setting the focus.
		* Optionally, extend one or both of L{onOk} or L{onCancel} to perform actions in response to the OK or Cancel buttons, respectively.

	@ivar title: The title of the dialog.
	@type title: str
	"""

	class MultiInstanceError(RuntimeError): pass

	_hasInstance=False

	title = ""
	shouldSuspendConfigProfileTriggers = True

	def __new__(cls, *args, **kwargs):
		if SettingsDialog._hasInstance:
			raise SettingsDialog.MultiInstanceError("Only one instance of SettingsDialog can exist at a time")
		obj = super(SettingsDialog, cls).__new__(cls, *args, **kwargs)
		SettingsDialog._hasInstance=True
		return obj

	def __init__(self, parent):
		"""
		@param parent: The parent for this dialog; C{None} for no parent.
		@type parent: wx.Window
		"""
		super(SettingsDialog, self).__init__(parent, wx.ID_ANY, self.title)
		mainSizer=wx.BoxSizer(wx.VERTICAL)
		self.settingsSizer=wx.BoxSizer(wx.VERTICAL)
		self.makeSettings(self.settingsSizer)

		mainSizer.Add(self.settingsSizer, border=guiHelper.BORDER_FOR_DIALOGS, flag=wx.ALL)
		mainSizer.Add(wx.StaticLine(self), flag=wx.EXPAND)
		mainSizer.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL), border=guiHelper.BORDER_FOR_DIALOGS, flag=wx.ALL|wx.ALIGN_RIGHT)

		mainSizer.Fit(self)
		self.SetSizer(mainSizer)

		self.Bind(wx.EVT_BUTTON,self.onOk,id=wx.ID_OK)
		self.Bind(wx.EVT_BUTTON,self.onCancel,id=wx.ID_CANCEL)
		self.postInit()
		self.Center(wx.BOTH | wx.CENTER_ON_SCREEN)

	def __del__(self):
		SettingsDialog._hasInstance=False

	def makeSettings(self, sizer):
		"""Populate the dialog with settings controls.
		Subclasses must override this method.
		@param sizer: The sizer to which to add the settings controls.
		@type sizer: wx.Sizer
		"""
		raise NotImplementedError

	def postInit(self):
		"""Called after the dialog has been created.
		For example, this might be used to set focus to the desired control.
		Sub-classes may override this method.
		"""

	def onOk(self, evt):
		"""Take action in response to the OK button being pressed.
		Sub-classes may extend this method.
		This base method should always be called to clean up the dialog.
		"""
		self.Destroy()

	def onCancel(self, evt):
		"""Take action in response to the Cancel button being pressed.
		Sub-classes may extend this method.
		This base method should always be called to clean up the dialog.
		"""
		self.Destroy()

class GeneralSettingsDialog(SettingsDialog):
	# Translators: This is the label for the general settings dialog.
	title = _("General Settings")
	LOG_LEVELS = (
		# Translators: One of the log levels of NVDA (the info mode shows info as NVDA runs).
		(log.INFO, _("info")),
		# Translators: One of the log levels of NVDA (the debug warning shows debugging messages and warnings as NVDA runs).
		(log.DEBUGWARNING, _("debug warning")),
		# Translators: One of the log levels of NVDA (the input/output shows keyboard commands and/or braille commands as well as speech and/or braille output of NVDA).
		(log.IO, _("input/output")),
		# Translators: One of the log levels of NVDA (the debug mode shows debug messages as NVDA runs).
		(log.DEBUG, _("debug"))
	)

	def makeSettings(self, settingsSizer):
		settingsSizerHelper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		self.languageNames = languageHandler.getAvailableLanguages()
		languageChoices = [x[1] for x in self.languageNames]
		# Translators: The label for a setting in general settings to select NVDA's interface language (once selected, NVDA must be restarted; the option user default means the user's Windows language will be used).
		languageLabelText = _("&Language (requires restart to fully take effect):")
		self.languageList=settingsSizerHelper.addLabeledControl(languageLabelText, wx.Choice, choices=languageChoices)
		self.languageList.SetToolTip(wx.ToolTip("Choose the language NVDA's messages and user interface should be presented in."))
		try:
			self.oldLanguage=config.conf["general"]["language"]
			index=[x[0] for x in self.languageNames].index(self.oldLanguage)
			self.languageList.SetSelection(index)
		except:
			pass
		if globalVars.appArgs.secure:
			self.languageList.Disable()

		# Translators: The label for a setting in general settings to save current configuration when NVDA exits (if it is not checked, user needs to save configuration before quitting NVDA).
		self.saveOnExitCheckBox=wx.CheckBox(self,label=_("&Save configuration on exit"))
		self.saveOnExitCheckBox.SetValue(config.conf["general"]["saveConfigurationOnExit"])
		if globalVars.appArgs.secure:
			self.saveOnExitCheckBox.Disable()
		settingsSizerHelper.addItem(self.saveOnExitCheckBox)

		# Translators: The label for a setting in general settings to ask before quitting NVDA (if not checked, NVDA will exit without asking the user for action).
		self.askToExitCheckBox=wx.CheckBox(self,label=_("Sho&w exit options when exiting NVDA"))
		self.askToExitCheckBox.SetValue(config.conf["general"]["askToExit"])
		settingsSizerHelper.addItem(self.askToExitCheckBox)

		# Translators: The label for a setting in general settings to play sounds when NVDA starts or exits.
		self.playStartAndExitSoundsCheckBox=wx.CheckBox(self,label=_("&Play sounds when starting or exiting NVDA"))
		self.playStartAndExitSoundsCheckBox.SetValue(config.conf["general"]["playStartAndExitSounds"])
		settingsSizerHelper.addItem(self.playStartAndExitSoundsCheckBox)

		# Translators: The label for a setting in general settings to select logging level of NVDA as it runs (available options and what they are logged are found under comments for the logging level messages themselves).
		logLevelLabelText=_("L&ogging level:")
		logLevelChoices = [name for level, name in self.LOG_LEVELS]
		self.logLevelList = settingsSizerHelper.addLabeledControl(logLevelLabelText, wx.Choice, choices=logLevelChoices)
		curLevel = log.getEffectiveLevel()
		for index, (level, name) in enumerate(self.LOG_LEVELS):
			if level == curLevel:
				self.logLevelList.SetSelection(index)
				break
		else:
			log.debugWarning("Could not set log level list to current log level")

		# Translators: The label for a setting in general settings to allow NVDA to start after logging onto Windows (if checked, NvDA will start automatically after loggin into Windows; if not, user must start NVDA by pressing the shortcut key (CTRL+Alt+N by default).
		self.startAfterLogonCheckBox = wx.CheckBox(self, label=_("&Automatically start NVDA after I log on to Windows"))
		self.startAfterLogonCheckBox.SetValue(config.getStartAfterLogon())
		if globalVars.appArgs.secure or not config.isInstalledCopy():
			self.startAfterLogonCheckBox.Disable()
		settingsSizerHelper.addItem(self.startAfterLogonCheckBox)

		# Translators: The label for a setting in general settings to allow NVDA to come up in Windows login screen (useful if user needs to enter passwords or if multiple user accounts are present to allow user to choose the correct account).
		self.startOnLogonScreenCheckBox = wx.CheckBox(self, label=_("Use NVDA on the Windows logon screen (requires administrator privileges)"))
		self.startOnLogonScreenCheckBox.SetValue(config.getStartOnLogonScreen())
		if globalVars.appArgs.secure or not config.canStartOnSecureScreens():
			self.startOnLogonScreenCheckBox.Disable()
		settingsSizerHelper.addItem(self.startOnLogonScreenCheckBox)

		# Translators: The label for a button in general settings to copy current user settings to system settings (to allow current settings to be used in secure screens such as User Account Control (UAC) dialog).
		self.copySettingsButton= wx.Button(self, label=_("Use currently saved settings on the logon and other secure screens (requires administrator privileges)"))
		self.copySettingsButton.Bind(wx.EVT_BUTTON,self.onCopySettings)
		if globalVars.appArgs.secure or not config.canStartOnSecureScreens():
			self.copySettingsButton.Disable()
		settingsSizerHelper.addItem(self.copySettingsButton)
		if updateCheck:
			# Translators: The label of a checkbox in general settings to toggle automatic checking for updated versions of NVDA (if not checked, user must check for updates manually).
			item=self.autoCheckForUpdatesCheckBox=wx.CheckBox(self,label=_("Automatically check for &updates to NVDA"))
			item.Value=config.conf["update"]["autoCheck"]
			if globalVars.appArgs.secure:
				item.Disable()
			settingsSizerHelper.addItem(item)

	def postInit(self):
		self.languageList.SetFocus()

	def onCopySettings(self,evt):
		for packageType in ('addons','appModules','globalPlugins','brailleDisplayDrivers','synthDrivers'):
			if len(os.listdir(os.path.join(globalVars.appArgs.configPath,packageType)))>0:
				if gui.messageBox(
					# Translators: A message to warn the user when attempting to copy current settings to system settings.
					_("Add-ons were detected in your user settings directory. Copying these to the system profile could be a security risk. Do you still wish to copy your settings?"),
					# Translators: The title of the warning dialog displayed when trying to copy settings for use in secure screens.
					_("Warning"),wx.YES|wx.NO|wx.ICON_WARNING,self
				)==wx.NO:
					return
				break
		progressDialog = gui.IndeterminateProgressDialog(gui.mainFrame,
		# Translators: The title of the dialog presented while settings are being copied 
		_("Copying Settings"),
		# Translators: The message displayed while settings are being copied to the system configuration (for use on Windows logon etc) 
		_("Please wait while settings are copied to the system configuration."))
		while True:
			try:
				gui.ExecAndPump(config.setSystemConfigToCurrentConfig)
				res=True
				break
			except installer.RetriableFailure:
				log.debugWarning("Error when copying settings to system config",exc_info=True)
				# Translators: a message dialog asking to retry or cancel when copying settings  fails
				message=_("Unable to copy a file. Perhaps it is currently being used by another process or you have run out of disc space on the drive you are copying to.")
				# Translators: the title of a retry cancel dialog when copying settings  fails
				title=_("Error Copying")
				if winUser.MessageBox(None,message,title,winUser.MB_RETRYCANCEL)==winUser.IDRETRY:
					continue
				res=False
				break
			except:
				log.debugWarning("Error when copying settings to system config",exc_info=True)
				res=False
				break
		progressDialog.done()
		del progressDialog
		if not res:
			# Translators: The message displayed when errors were found while trying to copy current configuration to system settings.
			gui.messageBox(_("Error copying NVDA user settings"),_("Error"),wx.OK|wx.ICON_ERROR,self)
		else:
			# Translators: The message displayed when copying configuration to system settings was successful.
			gui.messageBox(_("Successfully copied NVDA user settings"),_("Success"),wx.OK|wx.ICON_INFORMATION,self)

	def onOk(self,evt):
		newLanguage=[x[0] for x in self.languageNames][self.languageList.GetSelection()]
		config.conf["general"]["language"]=newLanguage
		config.conf["general"]["saveConfigurationOnExit"]=self.saveOnExitCheckBox.IsChecked()
		config.conf["general"]["askToExit"]=self.askToExitCheckBox.IsChecked()
		config.conf["general"]["playStartAndExitSounds"]=self.playStartAndExitSoundsCheckBox.IsChecked()
		logLevel=self.LOG_LEVELS[self.logLevelList.GetSelection()][0]
		config.conf["general"]["loggingLevel"]=logHandler.levelNames[logLevel]
		logHandler.setLogLevelFromConfig()
		if self.startAfterLogonCheckBox.IsEnabled():
			config.setStartAfterLogon(self.startAfterLogonCheckBox.GetValue())
		if self.startOnLogonScreenCheckBox.IsEnabled():
			try:
				config.setStartOnLogonScreen(self.startOnLogonScreenCheckBox.GetValue())
			except (WindowsError, RuntimeError):
				gui.messageBox(_("This change requires administrator privileges."), _("Insufficient Privileges"), style=wx.OK | wx.ICON_ERROR, parent=self)
		if updateCheck:
			config.conf["update"]["autoCheck"]=self.autoCheckForUpdatesCheckBox.IsChecked()
			updateCheck.terminate()
			updateCheck.initialize()
		if self.oldLanguage!=newLanguage:
			if gui.messageBox(
				# Translators: The message displayed after NVDA interface language has been changed.
				_("For the new language to take effect, the configuration must be saved and NVDA must be restarted. Press enter to save and restart NVDA, or cancel to manually save and exit at a later time."),
				# Translators: The title of the dialog which appears when the user changed NVDA's interface language.
				_("Language Configuration Change"),wx.OK|wx.CANCEL|wx.ICON_WARNING,self
			)==wx.OK:
				config.conf.save()
				queueHandler.queueFunction(queueHandler.eventQueue,core.restart)
		super(GeneralSettingsDialog, self).onOk(evt)

class SynthesizerDialog(SettingsDialog):
	# Translators: This is the label for the synthesizer dialog.
	title = _("Synthesizer")

	def makeSettings(self, settingsSizer):
		settingsSizerHelper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		# Translators: This is a label for the select
		# synthesizer combobox in the synthesizer dialog.
		synthListLabelText=_("&Synthesizer:")
		driverList=getSynthList()
		self.synthNames=[x[0] for x in driverList]
		options=[x[1] for x in driverList]
		self.synthList = settingsSizerHelper.addLabeledControl(synthListLabelText, wx.Choice, choices=options)

		try:
			index=self.synthNames.index(getSynth().name)
			self.synthList.SetSelection(index)
		except:
			pass

		# Translators: This is the label for the select output
		# device combo in the synthesizer dialog. Examples of
		# of an output device are default soundcard, usb
		# headphones, etc.
		deviceListLabelText = _("Output &device:")
		deviceNames=nvwave.getOutputDeviceNames()
		self.deviceList = settingsSizerHelper.addLabeledControl(deviceListLabelText, wx.Choice, choices=deviceNames)

		try:
			selection = deviceNames.index(config.conf["speech"]["outputDevice"])
		except ValueError:
			selection = 0
		self.deviceList.SetSelection(selection)

		# Translators: This is a label for the audio ducking combo box in the Audio Settings dialog 
		duckingListLabelText=_("Audio &ducking mode:")
		self.duckingList=settingsSizerHelper.addLabeledControl(duckingListLabelText, wx.Choice, choices=audioDucking.audioDuckingModes)
		index=config.conf['audio']['audioDuckingMode']
		self.duckingList.SetSelection(index)
		if not audioDucking.isAudioDuckingSupported():
			self.duckingList.Disable()

	def postInit(self):
		self.synthList.SetFocus()

	def onOk(self,evt):
		config.conf["speech"]["outputDevice"]=self.deviceList.GetStringSelection()
		newSynth=self.synthNames[self.synthList.GetSelection()]
		if not setSynth(newSynth):
			# Translators: This message is presented when
			# NVDA is unable to load the selected
			# synthesizer.
			gui.messageBox(_("Could not load the %s synthesizer.")%newSynth,_("Synthesizer Error"),wx.OK|wx.ICON_WARNING,self)
			return 
		if audioDucking.isAudioDuckingSupported():
			index=self.duckingList.GetSelection()
			config.conf['audio']['audioDuckingMode']=index
			audioDucking.setAudioDuckingMode(index)
		super(SynthesizerDialog, self).onOk(evt)

class SynthSettingChanger(object):
	"""Functor which acts as calback for GUI events."""

	def __init__(self,setting):
		self.setting=setting

	def __call__(self,evt):
		val=evt.GetSelection()
		setattr(getSynth(),self.setting.name,val)

class StringSynthSettingChanger(SynthSettingChanger):
	"""Same as L{SynthSettingChanger} but handles combobox events."""
	def __init__(self,setting,dialog):
		self.dialog=dialog
		super(StringSynthSettingChanger,self).__init__(setting)

	def __call__(self,evt):
		if self.setting.name=="voice":
			# Cancel speech first so that the voice will change immediately instead of the change being queued.
			speech.cancelSpeech()
			changeVoice(getSynth(),getattr(self.dialog,"_%ss"%self.setting.name)[evt.GetSelection()].ID)
			self.dialog.updateVoiceSettings(changedSetting=self.setting.name)
		else:
			setattr(getSynth(),self.setting.name,getattr(self.dialog,"_%ss"%self.setting.name)[evt.GetSelection()].ID)

class VoiceSettingsSlider(wx.Slider):

	def __init__(self,*args, **kwargs):
		super(VoiceSettingsSlider,self).__init__(*args,**kwargs)
		self.Bind(wx.EVT_CHAR, self.onSliderChar)

	def SetValue(self,i):
		super(VoiceSettingsSlider, self).SetValue(i)
		evt = wx.CommandEvent(wx.wxEVT_COMMAND_SLIDER_UPDATED,self.GetId())
		evt.SetInt(i)
		self.ProcessEvent(evt)
		# HACK: Win events don't seem to be sent for certain explicitly set values,
		# so send our own win event.
		# This will cause duplicates in some cases, but NVDA will filter them out.
		winUser.user32.NotifyWinEvent(winUser.EVENT_OBJECT_VALUECHANGE,self.Handle,winUser.OBJID_CLIENT,winUser.CHILDID_SELF)

	def onSliderChar(self, evt):
		key = evt.KeyCode
		if key == wx.WXK_UP:
			newValue = min(self.Value + self.LineSize, self.Max)
		elif key == wx.WXK_DOWN:
			newValue = max(self.Value - self.LineSize, self.Min)
		elif key == wx.WXK_PRIOR:
			newValue = min(self.Value + self.PageSize, self.Max)
		elif key == wx.WXK_NEXT:
			newValue = max(self.Value - self.PageSize, self.Min)
		elif key == wx.WXK_HOME:
			newValue = self.Max
		elif key == wx.WXK_END:
			newValue = self.Min
		else:
			evt.Skip()
			return
		self.SetValue(newValue)

class VoiceSettingsDialog(SettingsDialog):
	# Translators: This is the label for the voice settings dialog.
	title = _("Voice Settings")

	@classmethod
	def _setSliderStepSizes(cls, slider, setting):
		slider.SetLineSize(setting.minStep)
		slider.SetPageSize(setting.largeStep)

	def makeSettingControl(self,setting):
		"""Constructs appropriate GUI controls for given L{SynthSetting} such as label and slider.
		@param setting: Setting to construct controls for
		@type setting: L{SynthSetting}
		@returns: WXSizer containing newly created controls.
		@rtype: L{wx.BoxSizer}
		"""
		sizer=wx.BoxSizer(wx.HORIZONTAL)
		label=wx.StaticText(self,wx.ID_ANY,label="%s:"%setting.displayNameWithAccelerator)
		slider=VoiceSettingsSlider(self,wx.ID_ANY,minValue=0,maxValue=100)
		setattr(self,"%sSlider"%setting.name,slider)
		slider.Bind(wx.EVT_SLIDER,SynthSettingChanger(setting))
		self._setSliderStepSizes(slider,setting)
		slider.SetValue(getattr(getSynth(),setting.name))
		sizer.Add(label)
		sizer.Add(slider)
		if self.lastControl:
			slider.MoveAfterInTabOrder(self.lastControl)
		self.lastControl=slider
		return sizer

	def makeStringSettingControl(self,setting):
		"""Same as L{makeSettingControl} but for string settings. Returns sizer with label and combobox."""

		labelText="%s:"%setting.displayNameWithAccelerator
		synth=getSynth()
		setattr(self,"_%ss"%setting.name,getattr(synth,"available%ss"%setting.name.capitalize()).values())
		l=getattr(self,"_%ss"%setting.name)###
		labeledControl=guiHelper.LabeledControlHelper(self, labelText, wx.Choice, choices=[x.name for x in l])
		lCombo = labeledControl.control
		setattr(self,"%sList"%setting.name,lCombo)
		try:
			cur=getattr(synth,setting.name)
			i=[x.ID for x in l].index(cur)
			lCombo.SetSelection(i)
		except ValueError:
			pass
		lCombo.Bind(wx.EVT_CHOICE,StringSynthSettingChanger(setting,self))
		if self.lastControl:
			lCombo.MoveAfterInTabOrder(self.lastControl)
		self.lastControl=lCombo
		return labeledControl.sizer

	def makeBooleanSettingControl(self,setting):
		"""Same as L{makeSettingControl} but for boolean settings. Returns checkbox."""
		checkbox=wx.CheckBox(self,wx.ID_ANY,label=setting.displayNameWithAccelerator)
		setattr(self,"%sCheckbox"%setting.name,checkbox)
		checkbox.Bind(wx.EVT_CHECKBOX,
			lambda evt: setattr(getSynth(),setting.name,evt.IsChecked()))
		checkbox.SetValue(getattr(getSynth(),setting.name))
		if self.lastControl:
			checkbox.MoveAfterInTabOrder(self.lastControl)
		self.lastControl=checkbox
		return checkbox

	def makeSettings(self, settingsSizer):
		self.sizerDict={}
		self.lastControl=None
		#Create controls for Synth Settings
		self.updateVoiceSettings()

		settingsSizerHelper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		# Translators: This is the label for a checkbox in the
		# voice settings dialog (if checked, text will be read using the voice for the language of the text).
		autoLanguageSwitchingText = _("Automatic language switching (when supported)")
		self.autoLanguageSwitchingCheckbox = settingsSizerHelper.addItem(wx.CheckBox(self,label=autoLanguageSwitchingText))
		self.autoLanguageSwitchingCheckbox.SetValue(config.conf["speech"]["autoLanguageSwitching"])
		
		# Translators: This is the label for a checkbox in the
		# voice settings dialog (if checked, different voices for dialects will be used to read text in that dialect).
		autoDialectSwitchingText =_("Automatic dialect switching (when supported)")
		self.autoDialectSwitchingCheckbox=settingsSizerHelper.addItem(wx.CheckBox(self,label=autoDialectSwitchingText))
		self.autoDialectSwitchingCheckbox.SetValue(config.conf["speech"]["autoDialectSwitching"])

		# Translators: This is the label for a combobox in the
		# voice settings dialog (possible choices are none, some, most and all).
		punctuationLabelText = _("Punctuation/symbol &level:")
		symbolLevelLabels=characterProcessing.SPEECH_SYMBOL_LEVEL_LABELS
		symbolLevelChoices =[symbolLevelLabels[level] for level in characterProcessing.CONFIGURABLE_SPEECH_SYMBOL_LEVELS]
		self.symbolLevelList = settingsSizerHelper.addLabeledControl(punctuationLabelText, wx.Choice, choices=symbolLevelChoices)
		curLevel = config.conf["speech"]["symbolLevel"]
		self.symbolLevelList.SetSelection(characterProcessing.CONFIGURABLE_SPEECH_SYMBOL_LEVELS.index(curLevel))

		# Translators: This is the label for a checkbox in the
		# voice settings dialog (if checked, text will be read using the voice for the language of the text).
		trustVoiceLanguageText = _("Trust voice's language when processing characters and symbols")
		self.trustVoiceLanguageCheckbox = settingsSizerHelper.addItem(wx.CheckBox(self,label=trustVoiceLanguageText))
		self.trustVoiceLanguageCheckbox.SetValue(config.conf["speech"]["trustVoiceLanguage"])
		
		# Translators: This is a label for a setting in voice settings (an edit box to change voice pitch for capital letters; the higher the value, the pitch will be higher).
		capPitchChangeLabelText=_("Capital pitch change percentage")
		self.capPitchChangeEdit=settingsSizerHelper.addLabeledControl(capPitchChangeLabelText, nvdaControls.SelectOnFocusSpinCtrl,
			min=int(config.conf.getConfigValidationParameter(["speech", getSynth().name, "capPitchChange"], "min")),
			max=int(config.conf.getConfigValidationParameter(["speech", getSynth().name, "capPitchChange"], "max")),
			initial=config.conf["speech"][getSynth().name]["capPitchChange"])

		# Translators: This is the label for a checkbox in the
		# voice settings dialog.
		sayCapForCapsText = _("Say &cap before capitals")
		self.sayCapForCapsCheckBox = settingsSizerHelper.addItem(wx.CheckBox(self,label=sayCapForCapsText))
		self.sayCapForCapsCheckBox.SetValue(config.conf["speech"][getSynth().name]["sayCapForCapitals"])

		# Translators: This is the label for a checkbox in the
		# voice settings dialog.
		beepForCapsText =_("&Beep for capitals")
		self.beepForCapsCheckBox = settingsSizerHelper.addItem(wx.CheckBox(self, label = beepForCapsText))
		self.beepForCapsCheckBox.SetValue(config.conf["speech"][getSynth().name]["beepForCapitals"])

		# Translators: This is the label for a checkbox in the
		# voice settings dialog.
		useSpellingFunctionalityText = _("Use &spelling functionality if supported")
		self.useSpellingFunctionalityCheckBox = settingsSizerHelper.addItem(wx.CheckBox(self, label = useSpellingFunctionalityText))
		self.useSpellingFunctionalityCheckBox.SetValue(config.conf["speech"][getSynth().name]["useSpellingFunctionality"])

	def postInit(self):
		try:
			setting=getSynth().supportedSettings[0]
			control=getattr(self,"%sSlider"%setting.name) if isinstance(setting,NumericSynthSetting) else getattr(self,"%sList"%setting.name)
			control.SetFocus()
		except IndexError:
			self.symbolLevelList.SetFocus()

	def updateVoiceSettings(self, changedSetting=None):
		"""Creates, hides or updates existing GUI controls for all of supported settings."""
		synth=getSynth()
		#firstly check already created options
		for name,sizer in self.sizerDict.iteritems():
			if name == changedSetting:
				# Changing a setting shouldn't cause that setting itself to disappear.
				continue
			if not synth.isSupported(name):
				self.settingsSizer.Hide(sizer)
		#Create new controls, update already existing
		for setting in synth.supportedSettings:
			if setting.name == changedSetting:
				# Changing a setting shouldn't cause that setting's own values to change.
				continue
			if setting.name in self.sizerDict: #update a value
				self.settingsSizer.Show(self.sizerDict[setting.name])
				if isinstance(setting,NumericSynthSetting):
					getattr(self,"%sSlider"%setting.name).SetValue(getattr(synth,setting.name))
				elif isinstance(setting,BooleanSynthSetting):
					getattr(self,"%sCheckbox"%setting.name).SetValue(getattr(synth,setting.name))
				else:
					l=getattr(self,"_%ss"%setting.name)
					lCombo=getattr(self,"%sList"%setting.name)
					try:
						cur=getattr(synth,setting.name)
						i=[x.ID for x in l].index(cur)
						lCombo.SetSelection(i)
					except ValueError:
						pass
			else: #create a new control
				if isinstance(setting,NumericSynthSetting):
					settingMaker=self.makeSettingControl
				elif isinstance(setting,BooleanSynthSetting):
					settingMaker=self.makeBooleanSettingControl
				else:
					settingMaker=self.makeStringSettingControl
				s=settingMaker(setting)
				self.sizerDict[setting.name]=s
				self.settingsSizer.Insert(len(self.sizerDict)-1,s,border=10,flag=wx.BOTTOM)
		#Update graphical layout of the dialog
		self.settingsSizer.Layout()

	def onCancel(self,evt):
		#unbind change events for string settings as wx closes combo boxes on cancel
		for setting in getSynth().supportedSettings:
			if isinstance(setting,(NumericSynthSetting,BooleanSynthSetting)): continue
			getattr(self,"%sList"%setting.name).Unbind(wx.EVT_CHOICE)
		#restore settings
		getSynth().loadSettings()
		super(VoiceSettingsDialog, self).onCancel(evt)

	def onOk(self,evt):
		getSynth().saveSettings()
		config.conf["speech"]["autoLanguageSwitching"]=self.autoLanguageSwitchingCheckbox.IsChecked()
		config.conf["speech"]["autoDialectSwitching"]=self.autoDialectSwitchingCheckbox.IsChecked()
		config.conf["speech"]["symbolLevel"]=characterProcessing.CONFIGURABLE_SPEECH_SYMBOL_LEVELS[self.symbolLevelList.GetSelection()]
		config.conf["speech"]["trustVoiceLanguage"]=self.trustVoiceLanguageCheckbox.IsChecked()
		config.conf["speech"][getSynth().name]["capPitchChange"]=self.capPitchChangeEdit.Value
		config.conf["speech"][getSynth().name]["sayCapForCapitals"]=self.sayCapForCapsCheckBox.IsChecked()
		config.conf["speech"][getSynth().name]["beepForCapitals"]=self.beepForCapsCheckBox.IsChecked()
		config.conf["speech"][getSynth().name]["useSpellingFunctionality"]=self.useSpellingFunctionalityCheckBox.IsChecked()
		super(VoiceSettingsDialog, self).onOk(evt)

class KeyboardSettingsDialog(SettingsDialog):
	# Translators: This is the label for the keyboard settings dialog.
	title = _("Keyboard Settings")

	def makeSettings(self, settingsSizer):
		sHelper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		# Translators: This is the label for a combobox in the
		# keyboard settings dialog.
		kbdLabelText = _("&Keyboard layout:")
		layouts=keyboardHandler.KeyboardInputGesture.LAYOUTS
		self.kbdNames=sorted(layouts)
		kbdChoices = [layouts[layout] for layout in self.kbdNames]
		self.kbdList=sHelper.addLabeledControl(kbdLabelText, wx.Choice, choices=kbdChoices)
		try:
			index=self.kbdNames.index(config.conf['keyboard']['keyboardLayout'])
			self.kbdList.SetSelection(index)
		except:
			log.debugWarning("Could not set Keyboard layout list to current layout",exc_info=True) 

		# Translators: This is the label for a checkbox in the
		# keyboard settings dialog.
		capsAsNVDAText = _("Use CapsLock as an NVDA modifier key")
		self.capsAsNVDAModifierCheckBox=sHelper.addItem(wx.CheckBox(self,label=capsAsNVDAText))
		self.capsAsNVDAModifierCheckBox.SetValue(config.conf["keyboard"]["useCapsLockAsNVDAModifierKey"])

		# Translators: This is the label for a checkbox in the
		# keyboard settings dialog.
		numpadInsertAsModText = _("Use numpad Insert as an NVDA modifier key")
		self.numpadInsertAsNVDAModifierCheckBox=sHelper.addItem(wx.CheckBox(self,label=numpadInsertAsModText))
		self.numpadInsertAsNVDAModifierCheckBox.SetValue(config.conf["keyboard"]["useNumpadInsertAsNVDAModifierKey"])

		# Translators: This is the label for a checkbox in the
		# keyboard settings dialog.
		extendedInsertAsModText = _("Use extended Insert as an NVDA modifier key")
		self.extendedInsertAsNVDAModifierCheckBox=sHelper.addItem(wx.CheckBox(self,label=extendedInsertAsModText))
		self.extendedInsertAsNVDAModifierCheckBox.SetValue(config.conf["keyboard"]["useExtendedInsertAsNVDAModifierKey"])

		# Translators: This is the label for a checkbox in the
		# keyboard settings dialog.
		charsText = _("Speak typed &characters")
		self.charsCheckBox=sHelper.addItem(wx.CheckBox(self,label=charsText))
		self.charsCheckBox.SetValue(config.conf["keyboard"]["speakTypedCharacters"])

		# Translators: This is the label for a checkbox in the
		# keyboard settings dialog.
		speakTypedWordsText = _("Speak typed &words")
		self.wordsCheckBox=sHelper.addItem(wx.CheckBox(self,label=speakTypedWordsText))
		self.wordsCheckBox.SetValue(config.conf["keyboard"]["speakTypedWords"])

		# Translators: This is the label for a checkbox in the
		# keyboard settings dialog.
		speechInterruptForCharText = _("Speech interrupt for typed characters")
		self.speechInterruptForCharsCheckBox=sHelper.addItem(wx.CheckBox(self,label=speechInterruptForCharText))
		self.speechInterruptForCharsCheckBox.SetValue(config.conf["keyboard"]["speechInterruptForCharacters"])

		# Translators: This is the label for a checkbox in the
		# keyboard settings dialog.
		speechInterruptForEnterText = _("Speech interrupt for Enter key")
		self.speechInterruptForEnterCheckBox=sHelper.addItem(wx.CheckBox(self,label=speechInterruptForEnterText))
		self.speechInterruptForEnterCheckBox.SetValue(config.conf["keyboard"]["speechInterruptForEnter"])

		# Translators: This is the label for a checkbox in the
		# keyboard settings dialog.
		allowSkimReadingInSayAllText = _("Allow skim &reading in Say All")
		self.skimReadingInSayAllCheckBox=sHelper.addItem(wx.CheckBox(self,label=allowSkimReadingInSayAllText))
		self.skimReadingInSayAllCheckBox.SetValue(config.conf["keyboard"]["allowSkimReadingInSayAll"])

		# Translators: This is the label for a checkbox in the
		# keyboard settings dialog.
		beepForLowercaseWithCapsLockText = _("Beep if typing lowercase letters when caps lock is on")
		self.beepLowercaseCheckBox=sHelper.addItem(wx.CheckBox(self,label=beepForLowercaseWithCapsLockText))
		self.beepLowercaseCheckBox.SetValue(config.conf["keyboard"]["beepForLowercaseWithCapslock"])

		# Translators: This is the label for a checkbox in the
		# keyboard settings dialog.
		commandKeysText = _("Speak command &keys")
		self.commandKeysCheckBox=sHelper.addItem(wx.CheckBox(self,label=commandKeysText))
		self.commandKeysCheckBox.SetValue(config.conf["keyboard"]["speakCommandKeys"])

		# Translators: This is the label for a checkbox in the
		# keyboard settings dialog.
		alertForSpellingErrorsText = _("Play sound for &spelling errors while typing")
		self.alertForSpellingErrorsCheckBox=sHelper.addItem(wx.CheckBox(self,label=alertForSpellingErrorsText))
		self.alertForSpellingErrorsCheckBox.SetValue(config.conf["keyboard"]["alertForSpellingErrors"])
		if not config.conf["documentFormatting"]["reportSpellingErrors"]:
			self.alertForSpellingErrorsCheckBox.Disable()

		# Translators: This is the label for a checkbox in the
		# keyboard settings dialog.
		handleInjectedKeysText = _("Handle keys from other &applications")
		self.handleInjectedKeysCheckBox=sHelper.addItem(wx.CheckBox(self,label=handleInjectedKeysText))
		self.handleInjectedKeysCheckBox.SetValue(config.conf["keyboard"]["handleInjectedKeys"])

	def postInit(self):
		self.kbdList.SetFocus()

	def onOk(self,evt):
		# #2871: check wether at least one key is the nvda key.
		if not self.capsAsNVDAModifierCheckBox.IsChecked() and not self.numpadInsertAsNVDAModifierCheckBox.IsChecked() and not self.extendedInsertAsNVDAModifierCheckBox.IsChecked():
			log.debugWarning("No NVDA key set")
			gui.messageBox(
				# Translators: Message to report wrong configuration of the NVDA key
				_("At least one key must be used as the NVDA key."), 
				# Translators: The title of the message box
				_("Error"), wx.OK|wx.ICON_ERROR,self)
			return
		layout=self.kbdNames[self.kbdList.GetSelection()]
		config.conf['keyboard']['keyboardLayout']=layout
		config.conf["keyboard"]["useCapsLockAsNVDAModifierKey"]=self.capsAsNVDAModifierCheckBox.IsChecked()
		config.conf["keyboard"]["useNumpadInsertAsNVDAModifierKey"]=self.numpadInsertAsNVDAModifierCheckBox.IsChecked()
		config.conf["keyboard"]["useExtendedInsertAsNVDAModifierKey"]=self.extendedInsertAsNVDAModifierCheckBox.IsChecked()
		config.conf["keyboard"]["speakTypedCharacters"]=self.charsCheckBox.IsChecked()
		config.conf["keyboard"]["speakTypedWords"]=self.wordsCheckBox.IsChecked()
		config.conf["keyboard"]["speechInterruptForCharacters"]=self.speechInterruptForCharsCheckBox.IsChecked()
		config.conf["keyboard"]["speechInterruptForEnter"]=self.speechInterruptForEnterCheckBox.IsChecked()
		config.conf["keyboard"]["allowSkimReadingInSayAll"]=self.skimReadingInSayAllCheckBox.IsChecked()
		config.conf["keyboard"]["beepForLowercaseWithCapslock"]=self.beepLowercaseCheckBox.IsChecked()
		config.conf["keyboard"]["speakCommandKeys"]=self.commandKeysCheckBox.IsChecked()
		config.conf["keyboard"]["alertForSpellingErrors"]=self.alertForSpellingErrorsCheckBox.IsChecked()
		config.conf["keyboard"]["handleInjectedKeys"]=self.handleInjectedKeysCheckBox.IsChecked()
		super(KeyboardSettingsDialog, self).onOk(evt)

class MouseSettingsDialog(SettingsDialog):
	# Translators: This is the label for the mouse settings dialog.
	title = _("Mouse Settings")

	def makeSettings(self, settingsSizer):
		sHelper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

		# Translators: This is the label for a checkbox in the
		# mouse settings dialog.
		shapeChangesText = _("Report mouse &shape changes")
		self.shapeCheckBox=sHelper.addItem(wx.CheckBox(self,label=shapeChangesText))
		self.shapeCheckBox.SetValue(config.conf["mouse"]["reportMouseShapeChanges"])

		# Translators: This is the label for a checkbox in the
		# mouse settings dialog.
		mouseTrackingText=_("Enable mouse &tracking")
		self.mouseTrackingCheckBox=sHelper.addItem(wx.CheckBox(self,label=mouseTrackingText))
		self.mouseTrackingCheckBox.SetValue(config.conf["mouse"]["enableMouseTracking"])

		# Translators: This is the label for a combobox in the
		# mouse settings dialog.
		textUnitLabelText=_("Text &unit resolution:")
		import textInfos
		self.textUnits=[textInfos.UNIT_CHARACTER,textInfos.UNIT_WORD,textInfos.UNIT_LINE,textInfos.UNIT_PARAGRAPH]
		textUnitsChoices = [textInfos.unitLabels[x] for x in self.textUnits]
		self.textUnitComboBox=sHelper.addLabeledControl(textUnitLabelText, wx.Choice, choices=textUnitsChoices)
		try:
			index=self.textUnits.index(config.conf["mouse"]["mouseTextUnit"])
		except:
			index=0
		self.textUnitComboBox.SetSelection(index)

		# Translators: This is the label for a checkbox in the
		# mouse settings dialog.
		reportObjectRoleText = _("Report &role when mouse enters object")
		self.reportObjectRoleCheckBox=sHelper.addItem(wx.CheckBox(self,label=reportObjectRoleText))
		self.reportObjectRoleCheckBox.SetValue(config.conf["mouse"]["reportObjectRoleOnMouseEnter"])

		# Translators: This is the label for a checkbox in the
		# mouse settings dialog.
		audioText = _("&Play audio coordinates when mouse moves")
		self.audioCheckBox=sHelper.addItem(wx.CheckBox(self,label=audioText))
		self.audioCheckBox.SetValue(config.conf["mouse"]["audioCoordinatesOnMouseMove"])

		# Translators: This is the label for a checkbox in the
		# mouse settings dialog.
		audioDetectBrightnessText = _("&Brightness controls audio coordinates volume")
		self.audioDetectBrightnessCheckBox=sHelper.addItem(wx.CheckBox(self,label=audioDetectBrightnessText))
		self.audioDetectBrightnessCheckBox.SetValue(config.conf["mouse"]["audioCoordinates_detectBrightness"])

	def postInit(self):
		self.shapeCheckBox.SetFocus()

	def onOk(self,evt):
		config.conf["mouse"]["reportMouseShapeChanges"]=self.shapeCheckBox.IsChecked()
		config.conf["mouse"]["enableMouseTracking"]=self.mouseTrackingCheckBox.IsChecked()
		config.conf["mouse"]["mouseTextUnit"]=self.textUnits[self.textUnitComboBox.GetSelection()]
		config.conf["mouse"]["reportObjectRoleOnMouseEnter"]=self.reportObjectRoleCheckBox.IsChecked()
		config.conf["mouse"]["audioCoordinatesOnMouseMove"]=self.audioCheckBox.IsChecked()
		config.conf["mouse"]["audioCoordinates_detectBrightness"]=self.audioDetectBrightnessCheckBox.IsChecked()

		super(MouseSettingsDialog, self).onOk(evt)

class ReviewCursorDialog(SettingsDialog):
	# Translators: This is the label for the review cursor settings dialog.
	title = _("Review Cursor Settings")

	def makeSettings(self, settingsSizer):
		# Translators: This is the label for a checkbox in the
		# review cursor settings dialog.
		self.followFocusCheckBox=wx.CheckBox(self,wx.NewId(),label=_("Follow system &focus"))
		self.followFocusCheckBox.SetValue(config.conf["reviewCursor"]["followFocus"])
		settingsSizer.Add(self.followFocusCheckBox,border=10,flag=wx.BOTTOM)
		# Translators: This is the label for a checkbox in the
		# review cursor settings dialog.
		self.followCaretCheckBox=wx.CheckBox(self,wx.NewId(),label=_("Follow System &Caret"))
		self.followCaretCheckBox.SetValue(config.conf["reviewCursor"]["followCaret"])
		settingsSizer.Add(self.followCaretCheckBox,border=10,flag=wx.BOTTOM)
		# Translators: This is the label for a checkbox in the
		# review cursor settings dialog.
		self.followMouseCheckBox=wx.CheckBox(self,wx.NewId(),label=_("Follow &mouse cursor"))
		self.followMouseCheckBox.SetValue(config.conf["reviewCursor"]["followMouse"])
		settingsSizer.Add(self.followMouseCheckBox,border=10,flag=wx.BOTTOM)
		# Translators: This is the label for a checkbox in the
		# review cursor settings dialog.
		self.simpleReviewModeCheckBox=wx.CheckBox(self,wx.NewId(),label=_("Simple review mode"))
		self.simpleReviewModeCheckBox.SetValue(config.conf["reviewCursor"]["simpleReviewMode"])
		settingsSizer.Add(self.simpleReviewModeCheckBox,border=10,flag=wx.BOTTOM)

	def postInit(self):
		self.followFocusCheckBox.SetFocus()

	def onOk(self,evt):
		config.conf["reviewCursor"]["followFocus"]=self.followFocusCheckBox.IsChecked()
		config.conf["reviewCursor"]["followCaret"]=self.followCaretCheckBox.IsChecked()
		config.conf["reviewCursor"]["followMouse"]=self.followMouseCheckBox.IsChecked()
		config.conf["reviewCursor"]["simpleReviewMode"]=self.simpleReviewModeCheckBox.IsChecked()
		super(ReviewCursorDialog, self).onOk(evt)

class InputCompositionDialog(SettingsDialog):
	# Translators: This is the label for the Input Composition settings dialog.
	title = _("Input Composition Settings")

	def makeSettings(self, settingsSizer):
		# Translators: This is the label for a checkbox in the
		# Input composition settings dialog.
		self.autoReportAllCandidatesCheckBox=wx.CheckBox(self,wx.NewId(),label=_("Automatically report all available &candidates"))
		self.autoReportAllCandidatesCheckBox.SetValue(config.conf["inputComposition"]["autoReportAllCandidates"])
		settingsSizer.Add(self.autoReportAllCandidatesCheckBox,border=10,flag=wx.BOTTOM)
		# Translators: This is the label for a checkbox in the
		# Input composition settings dialog.
		self.announceSelectedCandidateCheckBox=wx.CheckBox(self,wx.NewId(),label=_("Announce &selected candidate"))
		self.announceSelectedCandidateCheckBox.SetValue(config.conf["inputComposition"]["announceSelectedCandidate"])
		settingsSizer.Add(self.announceSelectedCandidateCheckBox,border=10,flag=wx.BOTTOM)
		# Translators: This is the label for a checkbox in the
		# Input composition settings dialog.
		self.candidateIncludesShortCharacterDescriptionCheckBox=wx.CheckBox(self,wx.NewId(),label=_("Always include short character &description when announcing candidates"))
		self.candidateIncludesShortCharacterDescriptionCheckBox.SetValue(config.conf["inputComposition"]["alwaysIncludeShortCharacterDescriptionInCandidateName"])
		settingsSizer.Add(self.candidateIncludesShortCharacterDescriptionCheckBox,border=10,flag=wx.BOTTOM)
		# Translators: This is the label for a checkbox in the
		# Input composition settings dialog.
		self.reportReadingStringChangesCheckBox=wx.CheckBox(self,wx.NewId(),label=_("Report changes to the &reading string"))
		self.reportReadingStringChangesCheckBox.SetValue(config.conf["inputComposition"]["reportReadingStringChanges"])
		settingsSizer.Add(self.reportReadingStringChangesCheckBox,border=10,flag=wx.BOTTOM)
		# Translators: This is the label for a checkbox in the
		# Input composition settings dialog.
		self.reportCompositionStringChangesCheckBox=wx.CheckBox(self,wx.NewId(),label=_("Report changes to the &composition string"))
		self.reportCompositionStringChangesCheckBox.SetValue(config.conf["inputComposition"]["reportCompositionStringChanges"])
		settingsSizer.Add(self.reportCompositionStringChangesCheckBox,border=10,flag=wx.BOTTOM)

	def postInit(self):
		self.autoReportAllCandidatesCheckBox.SetFocus()

	def onOk(self,evt):
		config.conf["inputComposition"]["autoReportAllCandidates"]=self.autoReportAllCandidatesCheckBox.IsChecked()
		config.conf["inputComposition"]["announceSelectedCandidate"]=self.announceSelectedCandidateCheckBox.IsChecked()
		config.conf["inputComposition"]["alwaysIncludeShortCharacterDescriptionInCandidateName"]=self.candidateIncludesShortCharacterDescriptionCheckBox.IsChecked()
		config.conf["inputComposition"]["reportReadingStringChanges"]=self.reportReadingStringChangesCheckBox.IsChecked()
		config.conf["inputComposition"]["reportCompositionStringChanges"]=self.reportCompositionStringChangesCheckBox.IsChecked()
		super(InputCompositionDialog, self).onOk(evt)

class ObjectPresentationDialog(SettingsDialog):
	# Translators: This is the label for the object presentation dialog.
	title = _("Object Presentation")
	progressLabels = (
		# Translators: An option for progress bar output in the Object Presentation dialog
		# which disables reporting of progress bars.
		# See Progress bar output in the Object Presentation Settings section of the User Guide.
		("off", _("off")),
		# Translators: An option for progress bar output in the Object Presentation dialog
		# which reports progress bar updates by speaking.
		# See Progress bar output in the Object Presentation Settings section of the User Guide.
		("speak", _("Speak")),
		# Translators: An option for progress bar output in the Object Presentation dialog
		# which reports progress bar updates by beeping.
		# See Progress bar output in the Object Presentation Settings section of the User Guide.
		("beep", _("Beep")),
		# Translators: An option for progress bar output in the Object Presentation dialog
		# which reports progress bar updates by both speaking and beeping.
		# See Progress bar output in the Object Presentation Settings section of the User Guide.
		("both", _("Speak and beep")),
	)

	def makeSettings(self, settingsSizer):
		sHelper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		# Translators: This is the label for a checkbox in the
		# object presentation settings dialog.
		reportToolTipsText = _("Report &tooltips")
		self.tooltipCheckBox=sHelper.addItem(wx.CheckBox(self,label=reportToolTipsText))
		self.tooltipCheckBox.SetValue(config.conf["presentation"]["reportTooltips"])

		# Translators: This is the label for a checkbox in the
		# object presentation settings dialog.
		balloonText = _("Report &help balloons")
		self.balloonCheckBox=sHelper.addItem(wx.CheckBox(self,label=balloonText))
		self.balloonCheckBox.SetValue(config.conf["presentation"]["reportHelpBalloons"])

		# Translators: This is the label for a checkbox in the
		# object presentation settings dialog.
		shortcutText = _("Report object shortcut &keys")
		self.shortcutCheckBox=sHelper.addItem(wx.CheckBox(self,label=shortcutText))
		self.shortcutCheckBox.SetValue(config.conf["presentation"]["reportKeyboardShortcuts"])

		# Translators: This is the label for a checkbox in the
		# object presentation settings dialog.
		positionInfoText = _("Report object &position information")
		self.positionInfoCheckBox=sHelper.addItem(wx.CheckBox(self,label=positionInfoText))
		self.positionInfoCheckBox.SetValue(config.conf["presentation"]["reportObjectPositionInformation"])

		# Translators: This is the label for a checkbox in the
		# object presentation settings dialog.
		guessPositionInfoText=_("Guess object &position information when unavailable")
		self.guessPositionInfoCheckBox=sHelper.addItem(wx.CheckBox(self,label=guessPositionInfoText))
		self.guessPositionInfoCheckBox.SetValue(config.conf["presentation"]["guessObjectPositionInformationWhenUnavailable"])

		# Translators: This is the label for a checkbox in the
		# object presentation settings dialog.
		descriptionText = _("Report object &descriptions")
		self.descriptionCheckBox=sHelper.addItem(wx.CheckBox(self,label=descriptionText))
		self.descriptionCheckBox.SetValue(config.conf["presentation"]["reportObjectDescriptions"])
		
		# Translators: This is the label for a combobox in the
		# object presentation settings dialog.
		progressLabelText = _("Progress &bar output:")
		progressChoices = [name for setting, name in self.progressLabels]
		self.progressList=sHelper.addLabeledControl(progressLabelText, wx.Choice,choices=progressChoices)
		for index, (setting, name) in enumerate(self.progressLabels):
			if setting == config.conf["presentation"]["progressBarUpdates"]["progressBarOutputMode"]:
				self.progressList.SetSelection(index)
				break
		else:
			log.debugWarning("Could not set progress list to current report progress bar updates setting")
		
		# Translators: This is the label for a checkbox in the
		# object presentation settings dialog.
		reportBackgroundProgressBarsText = _("Report background progress bars")
		self.reportBackgroundProgressBarsCheckBox=sHelper.addItem(wx.CheckBox(self,label=reportBackgroundProgressBarsText))
		self.reportBackgroundProgressBarsCheckBox.SetValue(config.conf["presentation"]["progressBarUpdates"]["reportBackgroundProgressBars"])
		
		# Translators: This is the label for a checkbox in the
		# object presentation settings dialog.
		dynamicContentText = _("Report dynamic &content changes")
		self.dynamicContentCheckBox=sHelper.addItem(wx.CheckBox(self,label=dynamicContentText))
		self.dynamicContentCheckBox.SetValue(config.conf["presentation"]["reportDynamicContentChanges"])

		# Translators: This is the label for a combobox in the
		# object presentation settings dialog.
		autoSuggestionsLabelText = _("Play a sound when &auto-suggestions appear")
		self.autoSuggestionSoundsCheckBox=sHelper.addItem(wx.CheckBox(self,label=autoSuggestionsLabelText))
		self.autoSuggestionSoundsCheckBox.SetValue(config.conf["presentation"]["reportAutoSuggestionsWithSound"])

	def postInit(self):
		self.tooltipCheckBox.SetFocus()

	def onOk(self,evt):
		config.conf["presentation"]["reportTooltips"]=self.tooltipCheckBox.IsChecked()
		config.conf["presentation"]["reportHelpBalloons"]=self.balloonCheckBox.IsChecked()
		config.conf["presentation"]["reportKeyboardShortcuts"]=self.shortcutCheckBox.IsChecked()
		config.conf["presentation"]["reportObjectPositionInformation"]=self.positionInfoCheckBox.IsChecked()
		config.conf["presentation"]["guessObjectPositionInformationWhenUnavailable"]=self.guessPositionInfoCheckBox.IsChecked()
		config.conf["presentation"]["reportObjectDescriptions"]=self.descriptionCheckBox.IsChecked()
		config.conf["presentation"]["progressBarUpdates"]["progressBarOutputMode"]=self.progressLabels[self.progressList.GetSelection()][0]
		config.conf["presentation"]["progressBarUpdates"]["reportBackgroundProgressBars"]=self.reportBackgroundProgressBarsCheckBox.IsChecked()
		config.conf["presentation"]["reportDynamicContentChanges"]=self.dynamicContentCheckBox.IsChecked()
		config.conf["presentation"]["reportAutoSuggestionsWithSound"]=self.autoSuggestionSoundsCheckBox.IsChecked()
		super(ObjectPresentationDialog, self).onOk(evt)

class BrowseModeDialog(SettingsDialog):
	# Translators: This is the label for the browse mode settings dialog.
	title = _("Browse Mode")

	def makeSettings(self, settingsSizer):
		# Translators: This is the label for a textfield in the
		# browse mode settings dialog.
		maxLengthLabel=wx.StaticText(self,-1,label=_("&Maximum number of characters on one line"))
		settingsSizer.Add(maxLengthLabel)
		self.maxLengthEdit=nvdaControls.SelectOnFocusSpinCtrl(self,
			min=10, max=250, # min and max are not enforced in the config for virtualBuffers.maxLineLength
			initial=config.conf["virtualBuffers"]["maxLineLength"])
		settingsSizer.Add(self.maxLengthEdit,border=10,flag=wx.BOTTOM)
		# Translators: This is the label for a textfield in the
		# browse mode settings dialog.
		pageLinesLabel=wx.StaticText(self,-1,label=_("&Number of lines per page"))
		settingsSizer.Add(pageLinesLabel)
		self.pageLinesEdit=nvdaControls.SelectOnFocusSpinCtrl(self,
			min=5, max=150, # min and max are not enforced in the config for virtualBuffers.linesPerPage
			initial=config.conf["virtualBuffers"]["linesPerPage"])
		settingsSizer.Add(self.pageLinesEdit,border=10,flag=wx.BOTTOM)
		# Translators: This is the label for a checkbox in the
		# browse mode settings dialog.
		self.useScreenLayoutCheckBox=wx.CheckBox(self,wx.NewId(),label=_("Use &screen layout (when supported)"))
		self.useScreenLayoutCheckBox.SetValue(config.conf["virtualBuffers"]["useScreenLayout"])
		settingsSizer.Add(self.useScreenLayoutCheckBox,border=10,flag=wx.BOTTOM)
		# Translators: This is the label for a checkbox in the
		# browse mode settings dialog.
		self.autoSayAllCheckBox=wx.CheckBox(self,wx.NewId(),label=_("Automatic &Say All on page load"))
		self.autoSayAllCheckBox.SetValue(config.conf["virtualBuffers"]["autoSayAllOnPageLoad"])
		settingsSizer.Add(self.autoSayAllCheckBox,border=10,flag=wx.BOTTOM)
		# Translators: This is the label for a checkbox in the
		# browse mode settings dialog.
		self.layoutTablesCheckBox=wx.CheckBox(self,wx.NewId(),label=_("Include l&ayout tables"))
		self.layoutTablesCheckBox.SetValue(config.conf["documentFormatting"]["includeLayoutTables"])
		settingsSizer.Add(self.layoutTablesCheckBox,border=10,flag=wx.BOTTOM)
		# Translators: This is the label for a checkbox in the
		# browse mode settings dialog.
		self.autoPassThroughOnFocusChangeCheckBox=wx.CheckBox(self,wx.ID_ANY,label=_("Automatic focus mode for focus changes"))
		self.autoPassThroughOnFocusChangeCheckBox.SetValue(config.conf["virtualBuffers"]["autoPassThroughOnFocusChange"])
		settingsSizer.Add(self.autoPassThroughOnFocusChangeCheckBox,border=10,flag=wx.BOTTOM)
		# Translators: This is the label for a checkbox in the
		# browse mode settings dialog.
		self.autoPassThroughOnCaretMoveCheckBox=wx.CheckBox(self,wx.ID_ANY,label=_("Automatic focus mode for caret movement"))
		self.autoPassThroughOnCaretMoveCheckBox.SetValue(config.conf["virtualBuffers"]["autoPassThroughOnCaretMove"])
		settingsSizer.Add(self.autoPassThroughOnCaretMoveCheckBox,border=10,flag=wx.BOTTOM)
		# Translators: This is the label for a checkbox in the
		# browse mode settings dialog.
		self.passThroughAudioIndicationCheckBox=wx.CheckBox(self,wx.ID_ANY,label=_("Audio indication of focus and browse modes"))
		self.passThroughAudioIndicationCheckBox.SetValue(config.conf["virtualBuffers"]["passThroughAudioIndication"])
		settingsSizer.Add(self.passThroughAudioIndicationCheckBox,border=10,flag=wx.BOTTOM)
		# Translators: This is the label for a checkbox in the
		# browse mode settings dialog.
		self.trapNonCommandGesturesCheckBox=wx.CheckBox(self,wx.NewId(),label=_("&Trap all non-command gestures from reaching the document"))
		self.trapNonCommandGesturesCheckBox.SetValue(config.conf["virtualBuffers"]["trapNonCommandGestures"])
		settingsSizer.Add(self.trapNonCommandGesturesCheckBox,border=10,flag=wx.BOTTOM)

	def postInit(self):
		self.maxLengthEdit.SetFocus()

	def onOk(self,evt):
		config.conf["virtualBuffers"]["maxLineLength"]=self.maxLengthEdit.GetValue()
		config.conf["virtualBuffers"]["linesPerPage"]=self.pageLinesEdit.GetValue()
		config.conf["virtualBuffers"]["useScreenLayout"]=self.useScreenLayoutCheckBox.IsChecked()
		config.conf["virtualBuffers"]["autoSayAllOnPageLoad"]=self.autoSayAllCheckBox.IsChecked()
		config.conf["documentFormatting"]["includeLayoutTables"]=self.layoutTablesCheckBox.IsChecked()
		config.conf["virtualBuffers"]["autoPassThroughOnFocusChange"]=self.autoPassThroughOnFocusChangeCheckBox.IsChecked()
		config.conf["virtualBuffers"]["autoPassThroughOnCaretMove"]=self.autoPassThroughOnCaretMoveCheckBox.IsChecked()
		config.conf["virtualBuffers"]["passThroughAudioIndication"]=self.passThroughAudioIndicationCheckBox.IsChecked()
		config.conf["virtualBuffers"]["trapNonCommandGestures"]=self.trapNonCommandGesturesCheckBox.IsChecked()
		super(BrowseModeDialog, self).onOk(evt)

class DocumentFormattingDialog(SettingsDialog):
	# Translators: This is the label for the document formatting dialog.
	title = _("Document Formatting")

	def makeSettings(self, settingsSizer):
		sHelper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

		# Translators: This is a label appearing on the document formatting settings dialog.
		dialogText =_("The following options control the types of document formatting reported by NVDA.")
		sHelper.addItem(wx.StaticText(self, label=dialogText))

		scrolledPanel = scrolledpanel.ScrolledPanel(self, size = (500,400), style = wx.TAB_TRAVERSAL | wx.BORDER_THEME)
		self.scrolledPanel = scrolledPanel
		scrolledItems = guiHelper.BoxSizerHelper(scrolledPanel, orientation=wx.VERTICAL)
		scrolledItemsBorder = wx.BoxSizer(wx.VERTICAL)
		scrolledItemsBorder.Add(scrolledItems.sizer, border = guiHelper.BORDER_FOR_DIALOGS, flag = wx.ALL|wx.EXPAND)
		scrolledPanel.SetSizer(scrolledItemsBorder)

		# Translators: This is the label for a group of document formatting options in the 
		# document formatting settings dialog
		fontGroupText = _("Font")
		fontGroup = guiHelper.BoxSizerHelper(scrolledPanel, sizer=wx.StaticBoxSizer(wx.StaticBox(scrolledPanel, label=fontGroupText), wx.VERTICAL))
		scrolledItems.addItem(fontGroup)

		# Translators: This is the label for a checkbox in the
		# document formatting settings dialog.
		fontNameText = _("&Font name")
		self.fontNameCheckBox=fontGroup.addItem(wx.CheckBox(scrolledPanel, label=fontNameText))
		self.fontNameCheckBox.SetValue(config.conf["documentFormatting"]["reportFontName"])

		# Translators: This is the label for a checkbox in the
		# document formatting settings dialog.
		fontSizeText = _("Font &size")
		self.fontSizeCheckBox=fontGroup.addItem(wx.CheckBox(scrolledPanel,label=fontSizeText))
		self.fontSizeCheckBox.SetValue(config.conf["documentFormatting"]["reportFontSize"])
		
		# Translators: This is the label for a checkbox in the
		# document formatting settings dialog.
		fontAttributesText = _("Font attri&butes")
		self.fontAttrsCheckBox=fontGroup.addItem(wx.CheckBox(scrolledPanel,label=fontAttributesText))
		self.fontAttrsCheckBox.SetValue(config.conf["documentFormatting"]["reportFontAttributes"])

		# Translators: This is the label for a checkbox in the
		# document formatting settings dialog.
		emphasisText=_("E&mphasis")
		self.emphasisCheckBox=fontGroup.addItem(wx.CheckBox(scrolledPanel,label=emphasisText))
		self.emphasisCheckBox.SetValue(config.conf["documentFormatting"]["reportEmphasis"])

		# Translators: This is the label for a checkbox in the
		# document formatting settings dialog.
		styleText =_("St&yle")
		self.styleCheckBox=fontGroup.addItem(wx.CheckBox(scrolledPanel,label=styleText))
		self.styleCheckBox.SetValue(config.conf["documentFormatting"]["reportStyle"])
		
		# Translators: This is the label for a checkbox in the
		# document formatting settings dialog.
		colorsText = _("&Colors")
		self.colorCheckBox=fontGroup.addItem(wx.CheckBox(scrolledPanel,label=colorsText))
		self.colorCheckBox.SetValue(config.conf["documentFormatting"]["reportColor"])

		# Translators: This is the label for a group of document formatting options in the 
		# document formatting settings dialog
		documentInfoGroupText = _("Document information")
		docInfoGroup = guiHelper.BoxSizerHelper(scrolledPanel, sizer=wx.StaticBoxSizer(wx.StaticBox(scrolledPanel, label=documentInfoGroupText), wx.VERTICAL))
		scrolledItems.addItem(docInfoGroup)
		
		# Translators: This is the label for a checkbox in the
		# document formatting settings dialog.
		commentsText = _("Co&mments")
		self.commentsCheckBox=docInfoGroup.addItem(wx.CheckBox(scrolledPanel,label=commentsText))
		self.commentsCheckBox.SetValue(config.conf["documentFormatting"]["reportComments"])
		
		# Translators: This is the label for a checkbox in the
		# document formatting settings dialog.
		revisionsText = _("&Editor revisions")
		self.revisionsCheckBox=docInfoGroup.addItem(wx.CheckBox(scrolledPanel,label=revisionsText))
		self.revisionsCheckBox.SetValue(config.conf["documentFormatting"]["reportRevisions"])

		# Translators: This is the label for a checkbox in the
		# document formatting settings dialog.
		spellingErrorText = _("Spelling e&rrors")
		self.spellingErrorsCheckBox=docInfoGroup.addItem(wx.CheckBox(scrolledPanel,label=spellingErrorText))
		self.spellingErrorsCheckBox.SetValue(config.conf["documentFormatting"]["reportSpellingErrors"])

		# Translators: This is the label for a group of document formatting options in the 
		# document formatting settings dialog
		pageAndSpaceGroupText = _("Pages and spacing")
		pageAndSpaceGroup = guiHelper.BoxSizerHelper(scrolledPanel, sizer=wx.StaticBoxSizer(wx.StaticBox(scrolledPanel, label=pageAndSpaceGroupText), wx.VERTICAL))
		scrolledItems.addItem(pageAndSpaceGroup)

		# Translators: This is the label for a checkbox in the
		# document formatting settings dialog.
		pageText = _("&Pages")
		self.pageCheckBox=pageAndSpaceGroup.addItem(wx.CheckBox(scrolledPanel,label=pageText))
		self.pageCheckBox.SetValue(config.conf["documentFormatting"]["reportPage"])
		
		# Translators: This is the label for a checkbox in the
		# document formatting settings dialog.
		lineText = _("Line &numbers")
		self.lineNumberCheckBox=pageAndSpaceGroup.addItem(wx.CheckBox(scrolledPanel,label=lineText))
		self.lineNumberCheckBox.SetValue(config.conf["documentFormatting"]["reportLineNumber"])

		# Translators: This is the label for a combobox controlling the reporting of line indentation in the
		# Document  Formatting  dialog (possible choices are Off, Speech, Tones, or Both.
		lineIndentationText = _("Line &indentation reporting:")
		indentChoices=[
			#Translators: A choice in a combo box in the document formatting dialog  to report No  line Indentation.
			_("Off"),
			#Translators: A choice in a combo box in the document formatting dialog  to report indentation with Speech.
			pgettext('line indentation setting', "Speech"),
			#Translators: A choice in a combo box in the document formatting dialog  to report indentation with tones.
			_("Tones"),
			#Translators: A choice in a combo box in the document formatting dialog  to report indentation with both  Speech and tones.
			_("Both  Speech and Tones")
		]
		self.lineIndentationCombo = pageAndSpaceGroup.addLabeledControl(lineIndentationText, wx.Choice, choices=indentChoices)
		#We use bitwise operations because it saves us a four way if statement.
		curChoice = config.conf["documentFormatting"]["reportLineIndentationWithTones"] << 1 |  config.conf["documentFormatting"]["reportLineIndentation"]
		self.lineIndentationCombo.SetSelection(curChoice)

		# Translators: This message is presented in the document formatting settings dialogue
		# If this option is selected, NVDA will report paragraph indentation if available. 
		paragraphIndentationText = _("&Paragraph indentation")
		self.paragraphIndentationCheckBox=pageAndSpaceGroup.addItem(wx.CheckBox(scrolledPanel,label=paragraphIndentationText))
		self.paragraphIndentationCheckBox.SetValue(config.conf["documentFormatting"]["reportParagraphIndentation"])
		
		# Translators: This message is presented in the document formatting settings dialogue
		# If this option is selected, NVDA will report line spacing if available. 
		lineSpacingText=_("&Line spacing")
		self.lineSpacingCheckBox=pageAndSpaceGroup.addItem(wx.CheckBox(scrolledPanel,label=lineSpacingText))
		self.lineSpacingCheckBox.SetValue(config.conf["documentFormatting"]["reportLineSpacing"])

		# Translators: This is the label for a checkbox in the
		# document formatting settings dialog.
		alignmentText = _("&Alignment")
		self.alignmentCheckBox=pageAndSpaceGroup.addItem(wx.CheckBox(scrolledPanel,label=alignmentText))
		self.alignmentCheckBox.SetValue(config.conf["documentFormatting"]["reportAlignment"])

		# Translators: This is the label for a group of document formatting options in the 
		# document formatting settings dialog
		tablesGroupText = _("Table information")
		tablesGroup = guiHelper.BoxSizerHelper(scrolledPanel, sizer=wx.StaticBoxSizer(wx.StaticBox(scrolledPanel, label=tablesGroupText), wx.VERTICAL))
		scrolledItems.addItem(tablesGroup)

		# Translators: This is the label for a checkbox in the
		# document formatting settings dialog.
		self.tablesCheckBox=tablesGroup.addItem(wx.CheckBox(scrolledPanel,label=_("&Tables")))
		self.tablesCheckBox.SetValue(config.conf["documentFormatting"]["reportTables"])

		# Translators: This is the label for a checkbox in the
		# document formatting settings dialog.
		self.tableHeadersCheckBox=tablesGroup.addItem(wx.CheckBox(scrolledPanel,label=_("Row/column h&eaders")))
		self.tableHeadersCheckBox.SetValue(config.conf["documentFormatting"]["reportTableHeaders"])

		# Translators: This is the label for a checkbox in the
		# document formatting settings dialog.
		self.tableCellCoordsCheckBox=tablesGroup.addItem(wx.CheckBox(scrolledPanel,label=_("Cell c&oordinates")))
		self.tableCellCoordsCheckBox.SetValue(config.conf["documentFormatting"]["reportTableCellCoords"])

		borderChoices=[
			# Translators: This is the label for a combobox in the
			# document formatting settings dialog.
			_("Off"),
			# Translators: This is the label for a combobox in the
			# document formatting settings dialog.
			_("Styles"),
			# Translators: This is the label for a combobox in the
			# document formatting settings dialog.
			_("Both Colors and Styles"),
		]
		# Translators: This is the label for a combobox in the
		# document formatting settings dialog.
		self.borderComboBox=tablesGroup.addLabeledControl(_("Cell borders:"), wx.Choice, choices=borderChoices)
		curChoice = 0
		if config.conf["documentFormatting"]["reportBorderStyle"]:
			if config.conf["documentFormatting"]["reportBorderColor"]:
				curChoice = 2
			else:
				curChoice = 1
		self.borderComboBox.SetSelection(curChoice)
		
		# Translators: This is the label for a group of document formatting options in the 
		# document formatting settings dialog
		elementsGroupText = _("Elements")
		elementsGroup = guiHelper.BoxSizerHelper(scrolledPanel, sizer=wx.StaticBoxSizer(wx.StaticBox(scrolledPanel, label=elementsGroupText), wx.VERTICAL))
		scrolledItems.addItem(elementsGroup)

		# Translators: This is the label for a checkbox in the
		# document formatting settings dialog.
		self.headingsCheckBox=elementsGroup.addItem(wx.CheckBox(scrolledPanel,label=_("&Headings")))
		self.headingsCheckBox.SetValue(config.conf["documentFormatting"]["reportHeadings"])

		# Translators: This is the label for a checkbox in the
		# document formatting settings dialog.
		self.linksCheckBox=elementsGroup.addItem(wx.CheckBox(scrolledPanel,label=_("Lin&ks")))
		self.linksCheckBox.SetValue(config.conf["documentFormatting"]["reportLinks"])

		# Translators: This is the label for a checkbox in the
		# document formatting settings dialog.
		self.listsCheckBox=elementsGroup.addItem(wx.CheckBox(scrolledPanel,label=_("&Lists")))
		self.listsCheckBox.SetValue(config.conf["documentFormatting"]["reportLists"])

		# Translators: This is the label for a checkbox in the
		# document formatting settings dialog.
		self.blockQuotesCheckBox=elementsGroup.addItem(wx.CheckBox(scrolledPanel,label=_("Block &quotes")))
		self.blockQuotesCheckBox.SetValue(config.conf["documentFormatting"]["reportBlockQuotes"])
		
		# Translators: This is the label for a checkbox in the
		# document formatting settings dialog.
		self.landmarksCheckBox=elementsGroup.addItem(wx.CheckBox(scrolledPanel,label=_("Lan&dmarks")))
		self.landmarksCheckBox.SetValue(config.conf["documentFormatting"]["reportLandmarks"])
		
		# Translators: This is the label for a checkbox in the
		# document formatting settings dialog.
		self.framesCheckBox=elementsGroup.addItem(wx.CheckBox(scrolledPanel,label=_("Fra&mes")))
		self.framesCheckBox.Value=config.conf["documentFormatting"]["reportFrames"]
		
		# Translators: This is the label for a checkbox in the
		# document formatting settings dialog.
		self.clickableCheckBox=elementsGroup.addItem(wx.CheckBox(scrolledPanel,label=_("&Clickable")))
		self.clickableCheckBox.Value=config.conf["documentFormatting"]["reportClickable"]

		sHelper.addItem(scrolledPanel)
		scrolledPanel.SetAutoLayout(True)
		scrolledPanel.Layout()
		scrolledPanel.SetupScrolling()

		# Translators: This is the label for a checkbox in the
		# document formatting settings dialog.
		detectFormatAfterCursorText =_("Report formatting changes after the cursor (can cause a lag)")
		self.detectFormatAfterCursorCheckBox=wx.CheckBox(self, label=detectFormatAfterCursorText)
		self.detectFormatAfterCursorCheckBox.SetValue(config.conf["documentFormatting"]["detectFormatAfterCursor"])
		sHelper.addItem(self.detectFormatAfterCursorCheckBox)

	def postInit(self):
		self.scrolledPanel.SetFocus()

	def onOk(self,evt):
		config.conf["documentFormatting"]["detectFormatAfterCursor"]=self.detectFormatAfterCursorCheckBox.IsChecked()
		config.conf["documentFormatting"]["reportFontName"]=self.fontNameCheckBox.IsChecked()
		config.conf["documentFormatting"]["reportFontSize"]=self.fontSizeCheckBox.IsChecked()
		config.conf["documentFormatting"]["reportFontAttributes"]=self.fontAttrsCheckBox.IsChecked()
		config.conf["documentFormatting"]["reportColor"]=self.colorCheckBox.IsChecked()
		config.conf["documentFormatting"]["reportComments"]=self.commentsCheckBox.IsChecked()
		config.conf["documentFormatting"]["reportRevisions"]=self.revisionsCheckBox.IsChecked()
		config.conf["documentFormatting"]["reportEmphasis"]=self.emphasisCheckBox.IsChecked()
		config.conf["documentFormatting"]["reportAlignment"]=self.alignmentCheckBox.IsChecked()
		config.conf["documentFormatting"]["reportStyle"]=self.styleCheckBox.IsChecked()
		config.conf["documentFormatting"]["reportSpellingErrors"]=self.spellingErrorsCheckBox.IsChecked()
		config.conf["documentFormatting"]["reportPage"]=self.pageCheckBox.IsChecked()
		config.conf["documentFormatting"]["reportLineNumber"]=self.lineNumberCheckBox.IsChecked()
		choice = self.lineIndentationCombo.GetSelection()
		config.conf["documentFormatting"]["reportLineIndentation"] = choice in (1, 3)
		config.conf["documentFormatting"]["reportLineIndentationWithTones"] = choice in (2, 3)
		config.conf["documentFormatting"]["reportParagraphIndentation"]=self.paragraphIndentationCheckBox.IsChecked()
		config.conf["documentFormatting"]["reportLineSpacing"]=self.lineSpacingCheckBox.IsChecked()
		config.conf["documentFormatting"]["reportTables"]=self.tablesCheckBox.IsChecked()
		config.conf["documentFormatting"]["reportTableHeaders"]=self.tableHeadersCheckBox.IsChecked()
		config.conf["documentFormatting"]["reportTableCellCoords"]=self.tableCellCoordsCheckBox.IsChecked()
		choice = self.borderComboBox.GetSelection()
		config.conf["documentFormatting"]["reportBorderStyle"] = choice in (1,2)
		config.conf["documentFormatting"]["reportBorderColor"] = (choice == 2)
		config.conf["documentFormatting"]["reportLinks"]=self.linksCheckBox.IsChecked()
		config.conf["documentFormatting"]["reportHeadings"]=self.headingsCheckBox.IsChecked()
		config.conf["documentFormatting"]["reportLists"]=self.listsCheckBox.IsChecked()
		config.conf["documentFormatting"]["reportBlockQuotes"]=self.blockQuotesCheckBox.IsChecked()
		config.conf["documentFormatting"]["reportLandmarks"]=self.landmarksCheckBox.IsChecked()
		config.conf["documentFormatting"]["reportFrames"]=self.framesCheckBox.Value
		config.conf["documentFormatting"]["reportClickable"]=self.clickableCheckBox.Value
		super(DocumentFormattingDialog, self).onOk(evt)

class UwpOcrDialog(SettingsDialog):
	# Translators: The title of the Windows 10 OCR dialog.
	title = _("Windows 10 OCR")

	def makeSettings(self, settingsSizer):
		sHelper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		# Lazily import this.
		from contentRecog import uwpOcr
		self.languageCodes = uwpOcr.getLanguages()
		languageChoices = [
			languageHandler.getLanguageDescription(languageHandler.normalizeLanguage(lang))
			for lang in self.languageCodes]
		# Translators: Label for an option in the Windows 10 OCR dialog.
		languageLabel = _("Recognition &language:")
		self.languageChoice = sHelper.addLabeledControl(languageLabel, wx.Choice, choices=languageChoices)
		try:
			langIndex = self.languageCodes.index(config.conf["uwpOcr"]["language"])
			self.languageChoice.Selection = langIndex
		except ValueError:
			self.languageChoice.Selection = 0

	def postInit(self):
		self.languageChoice.SetFocus()

	def onOk(self, evt):
		lang = self.languageCodes[self.languageChoice.Selection]
		config.conf["uwpOcr"]["language"] = lang
		super(UwpOcrDialog, self).onOk(evt)

class DictionaryEntryDialog(wx.Dialog):
	TYPE_LABELS = {
		# Translators: This is a label for an Entry Type radio button in add dictionary entry dialog.
		speechDictHandler.ENTRY_TYPE_ANYWHERE: _("&Anywhere"),
		# Translators: This is a label for an Entry Type radio button in add dictionary entry dialog.
		speechDictHandler.ENTRY_TYPE_WORD: _("Whole &word"),
		# Translators: This is a label for an Entry Type radio button in add dictionary entry dialog.
		speechDictHandler.ENTRY_TYPE_REGEXP: _("Regular &expression")
	}
	TYPE_LABELS_ORDERING = (speechDictHandler.ENTRY_TYPE_ANYWHERE, speechDictHandler.ENTRY_TYPE_WORD, speechDictHandler.ENTRY_TYPE_REGEXP)

	# Translators: This is the label for the edit dictionary entry dialog.
	def __init__(self, parent, title=_("Edit Dictionary Entry")):
		super(DictionaryEntryDialog,self).__init__(parent,title=title)
		mainSizer=wx.BoxSizer(wx.VERTICAL)
		sHelper = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)

		# Translators: This is a label for an edit field in add dictionary entry dialog.
		patternLabelText = _("&Pattern")
		self.patternTextCtrl=sHelper.addLabeledControl(patternLabelText, wx.TextCtrl)

		# Translators: This is a label for an edit field in add dictionary entry dialog and in punctuation/symbol pronunciation dialog.
		replacementLabelText = _("&Replacement")
		self.replacementTextCtrl=sHelper.addLabeledControl(replacementLabelText, wx.TextCtrl)

		# Translators: This is a label for an edit field in add dictionary entry dialog.
		commentLabelText = _("&Comment")
		self.commentTextCtrl=sHelper.addLabeledControl(commentLabelText, wx.TextCtrl)
		
		# Translators: This is a label for a checkbox in add dictionary entry dialog.
		caseSensitiveText = _("Case &sensitive")
		self.caseSensitiveCheckBox=sHelper.addItem(wx.CheckBox(self,label=caseSensitiveText))

		# Translators: This is a label for a set of radio buttons in add dictionary entry dialog.
		typeText = _("&Type")
		typeChoices = [DictionaryEntryDialog.TYPE_LABELS[i] for i in DictionaryEntryDialog.TYPE_LABELS_ORDERING]
		self.typeRadioBox=sHelper.addItem(wx.RadioBox(self,label=typeText, choices=typeChoices))
		
		sHelper.addDialogDismissButtons(self.CreateButtonSizer(wx.OK|wx.CANCEL))

		mainSizer.Add(sHelper.sizer,border=20,flag=wx.ALL)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)
		self.setType(speechDictHandler.ENTRY_TYPE_ANYWHERE)
		self.patternTextCtrl.SetFocus()
		self.Bind(wx.EVT_BUTTON,self.onOk,id=wx.ID_OK)

	def getType(self):
		typeRadioValue = self.typeRadioBox.GetSelection()
		if typeRadioValue == wx.NOT_FOUND:
			return speechDictHandler.ENTRY_TYPE_ANYWHERE
		return DictionaryEntryDialog.TYPE_LABELS_ORDERING[typeRadioValue]

	def onOk(self,evt):
		if not self.patternTextCtrl.GetValue():
			# Translators: This is an error message to let the user know that the pattern field in the dictionary entry is not valid.
			gui.messageBox(_("A pattern is required."), _("Dictionary Entry Error"), wx.OK|wx.ICON_WARNING, self)
			self.patternTextCtrl.SetFocus()
			return 
		try:
			self.dictEntry=speechDictHandler.SpeechDictEntry(self.patternTextCtrl.GetValue(),self.replacementTextCtrl.GetValue(),self.commentTextCtrl.GetValue(),bool(self.caseSensitiveCheckBox.GetValue()),self.getType())
		except Exception as e:
			log.debugWarning("Could not add dictionary entry due to (regex error) : %s" % e)
			# Translators: This is an error message to let the user know that the dictionary entry is not valid.
			gui.messageBox(_("Regular Expression error: \"%s\".")%e, _("Dictionary Entry Error"), wx.OK|wx.ICON_WARNING, self)
			return 
		evt.Skip()

	def setType(self, type):
		self.typeRadioBox.SetSelection(DictionaryEntryDialog.TYPE_LABELS_ORDERING.index(type))

class DictionaryDialog(SettingsDialog):
	TYPE_LABELS = {t: l.replace("&", "") for t, l in DictionaryEntryDialog.TYPE_LABELS.iteritems()}

	def __init__(self,parent,title,speechDict):
		self.title = title
		self.speechDict = speechDict
		self.tempSpeechDict=speechDictHandler.SpeechDict()
		self.tempSpeechDict.extend(self.speechDict)
		globalVars.speechDictionaryProcessing=False
		super(DictionaryDialog, self).__init__(parent)

	def makeSettings(self, settingsSizer):
		sHelper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		# Translators: The label for the combo box of dictionary entries in speech dictionary dialog.
		entriesLabelText=_("&Dictionary entries")
		self.dictList=sHelper.addLabeledControl(entriesLabelText, wx.ListCtrl, style=wx.LC_REPORT|wx.LC_SINGLE_SEL,size=(550,350))
		# Translators: The label for a column in dictionary entries list used to identify comments for the entry.
		self.dictList.InsertColumn(0,_("Comment"),width=150)
		# Translators: The label for a column in dictionary entries list used to identify pattern (original word or a pattern).
		self.dictList.InsertColumn(1,_("Pattern"),width=150)
		# Translators: The label for a column in dictionary entries list and in a list of symbols from symbol pronunciation dialog used to identify replacement for a pattern or a symbol
		self.dictList.InsertColumn(2,_("Replacement"),width=150)
		# Translators: The label for a column in dictionary entries list used to identify whether the entry is case sensitive or not.
		self.dictList.InsertColumn(3,_("case"),width=50)
		# Translators: The label for a column in dictionary entries list used to identify whether the entry is a regular expression, matches whole words, or matches anywhere.
		self.dictList.InsertColumn(4,_("Type"),width=50)
		self.offOn = (_("off"),_("on"))
		for entry in self.tempSpeechDict:
			self.dictList.Append((entry.comment,entry.pattern,entry.replacement,self.offOn[int(entry.caseSensitive)],DictionaryDialog.TYPE_LABELS[entry.type]))
		self.editingIndex=-1
		self.dictList.Bind(wx.EVT_CHAR, self.onListChar)

		bHelper = guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		addButtonID=wx.NewId()
		# Translators: The label for a button in speech dictionaries dialog to add new entries.
		bHelper.addButton(self, addButtonID,_("&Add"),wx.DefaultPosition)
		
		editButtonID=wx.NewId()
		# Translators: The label for a button in speech dictionaries dialog to edit existing entries.
		bHelper.addButton(self, editButtonID,_("&Edit"),wx.DefaultPosition)
		
		removeButtonID=wx.NewId()
		bHelper.addButton(self, removeButtonID,_("&Remove"),wx.DefaultPosition)
		sHelper.addItem(bHelper)

		self.Bind(wx.EVT_BUTTON,self.OnAddClick,id=addButtonID)
		self.Bind(wx.EVT_BUTTON,self.OnEditClick,id=editButtonID)
		self.Bind(wx.EVT_BUTTON,self.OnRemoveClick,id=removeButtonID)

	def postInit(self):
		self.dictList.SetFocus()

	def onListChar(self, evt):
		if evt.KeyCode == wx.WXK_RETURN:
			# The enter key should be propagated to the dialog and thus activate the default button,
			# but this is broken (wx ticket #3725).
			# Therefore, we must catch the enter key here.
			# Activate the OK button.
			self.ProcessEvent(wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK))
		else:
			evt.Skip()

	def onCancel(self,evt):
		globalVars.speechDictionaryProcessing=True
		super(DictionaryDialog, self).onCancel(evt)

	def onOk(self,evt):
		globalVars.speechDictionaryProcessing=True
		if self.tempSpeechDict!=self.speechDict:
			del self.speechDict[:]
			self.speechDict.extend(self.tempSpeechDict)
			self.speechDict.save()
		super(DictionaryDialog, self).onOk(evt)

	def OnAddClick(self,evt):
		# Translators: This is the label for the add dictionary entry dialog.
		entryDialog=DictionaryEntryDialog(self,title=_("Add Dictionary Entry"))
		if entryDialog.ShowModal()==wx.ID_OK:
			self.tempSpeechDict.append(entryDialog.dictEntry)
			self.dictList.Append((entryDialog.commentTextCtrl.GetValue(),entryDialog.patternTextCtrl.GetValue(),entryDialog.replacementTextCtrl.GetValue(),self.offOn[int(entryDialog.caseSensitiveCheckBox.GetValue())],DictionaryDialog.TYPE_LABELS[entryDialog.getType()]))
			index=self.dictList.GetFirstSelected()
			while index>=0:
				self.dictList.Select(index,on=0)
				index=self.dictList.GetNextSelected(index)
			addedIndex=self.dictList.GetItemCount()-1
			self.dictList.Select(addedIndex)
			self.dictList.Focus(addedIndex)
			self.dictList.SetFocus()
		entryDialog.Destroy()

	def OnEditClick(self,evt):
		if self.dictList.GetSelectedItemCount()!=1:
			return
		editIndex=self.dictList.GetFirstSelected()
		if editIndex<0:
			return
		entryDialog=DictionaryEntryDialog(self)
		entryDialog.patternTextCtrl.SetValue(self.tempSpeechDict[editIndex].pattern)
		entryDialog.replacementTextCtrl.SetValue(self.tempSpeechDict[editIndex].replacement)
		entryDialog.commentTextCtrl.SetValue(self.tempSpeechDict[editIndex].comment)
		entryDialog.caseSensitiveCheckBox.SetValue(self.tempSpeechDict[editIndex].caseSensitive)
		entryDialog.setType(self.tempSpeechDict[editIndex].type)
		if entryDialog.ShowModal()==wx.ID_OK:
			self.tempSpeechDict[editIndex]=entryDialog.dictEntry
			self.dictList.SetStringItem(editIndex,0,entryDialog.commentTextCtrl.GetValue())
			self.dictList.SetStringItem(editIndex,1,entryDialog.patternTextCtrl.GetValue())
			self.dictList.SetStringItem(editIndex,2,entryDialog.replacementTextCtrl.GetValue())
			self.dictList.SetStringItem(editIndex,3,self.offOn[int(entryDialog.caseSensitiveCheckBox.GetValue())])
			self.dictList.SetStringItem(editIndex,4,DictionaryDialog.TYPE_LABELS[entryDialog.getType()])
			self.dictList.SetFocus()
		entryDialog.Destroy()

	def OnRemoveClick(self,evt):
		index=self.dictList.GetFirstSelected()
		while index>=0:
			self.dictList.DeleteItem(index)
			del self.tempSpeechDict[index]
			index=self.dictList.GetNextSelected(index)
		self.dictList.SetFocus()

class BrailleSettingsDialog(SettingsDialog):
	# Translators: This is the label for the braille settings dialog.
	title = _("Braille Settings")

	def makeSettings(self, settingsSizer):
		sHelper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

		# Translators: The label for a setting in braille settings to choose a braille display.
		displayLabelText = _("Braille &display:")
		driverList = braille.getDisplayList()
		self.displayNames = [driver[0] for driver in driverList]
		displayChoices = [driver[1] for driver in driverList]
		self.displayList = sHelper.addLabeledControl(displayLabelText, wx.Choice, choices=displayChoices)
		self.Bind(wx.EVT_CHOICE, self.onDisplayNameChanged, self.displayList)
		try:
			selection = self.displayNames.index(braille.handler.display.name)
			self.displayList.SetSelection(selection)
		except:
			pass

		# Translators: The label for a setting in braille settings to choose the connection port (if the selected braille display supports port selection).
		portsLabelText = _("&Port:")
		self.portsList = sHelper.addLabeledControl(portsLabelText, wx.Choice, choices=[])
		self.updatePossiblePorts()

		tables = brailleTables.listTables()
		# Translators: The label for a setting in braille settings to select the output table (the braille table used to read braille text on the braille display).
		outputsLabelText = _("&Output table:")
		outTables = [table for table in tables if table.output]
		self.outTableNames = [table.fileName for table in outTables]
		outTableChoices = [table.displayName for table in outTables]
		self.outTableList = sHelper.addLabeledControl(outputsLabelText, wx.Choice, choices=outTableChoices)
		try:
			selection = self.outTableNames.index(config.conf["braille"]["translationTable"])
			self.outTableList.SetSelection(selection)
		except:
			pass

		# Translators: The label for a setting in braille settings to select the input table (the braille table used to type braille characters on a braille keyboard).
		inputLabelText = _("&Input table:")
		self.inTables = [table for table in tables if table.input]
		inTableChoices = [table.displayName for table in self.inTables]
		self.inTableList = sHelper.addLabeledControl(inputLabelText, wx.Choice, choices=inTableChoices)
		try:
			selection = self.inTables.index(brailleInput.handler.table)
			self.inTableList.SetSelection(selection)
		except:
			pass

		# Translators: The label for a setting in braille settings to expand the current word under cursor to computer braille.
		expandAtCursorText = _("E&xpand to computer braille for the word at the cursor")
		self.expandAtCursorCheckBox = sHelper.addItem(wx.CheckBox(self, wx.ID_ANY, label=expandAtCursorText))
		self.expandAtCursorCheckBox.SetValue(config.conf["braille"]["expandAtCursor"])

		# Translators: The label for a setting in braille settings to show the cursor.
		showCursorLabelText = _("&Show cursor")
		self.showCursorCheckBox = sHelper.addItem(wx.CheckBox(self, label=showCursorLabelText))
		self.showCursorCheckBox.Bind(wx.EVT_CHECKBOX, self.onShowCursorChange)
		self.showCursorCheckBox.SetValue(config.conf["braille"]["showCursor"])

		# Translators: The label for a setting in braille settings to enable cursor blinking.
		cursorBlinkLabelText = _("Blink cursor")
		self.cursorBlinkCheckBox = sHelper.addItem(wx.CheckBox(self, label=cursorBlinkLabelText))
		self.cursorBlinkCheckBox.Bind(wx.EVT_CHECKBOX, self.onBlinkCursorChange)
		self.cursorBlinkCheckBox.SetValue(config.conf["braille"]["cursorBlink"])
		if not self.showCursorCheckBox.GetValue():
			self.cursorBlinkCheckBox.Disable()

		# Translators: The label for a setting in braille settings to change cursor blink rate in milliseconds (1 second is 1000 milliseconds).
		cursorBlinkRateLabelText = _("Cursor blink rate (ms)")
		minBlinkRate = int(config.conf.getConfigValidationParameter(["braille", "cursorBlinkRate"], "min"))
		maxBlinkRate = int(config.conf.getConfigValidationParameter(["braille", "cursorBlinkRate"], "max"))
		self.cursorBlinkRateEdit = sHelper.addLabeledControl(cursorBlinkRateLabelText, nvdaControls.SelectOnFocusSpinCtrl,
			min=minBlinkRate, max=maxBlinkRate, initial=config.conf["braille"]["cursorBlinkRate"])
		if not self.showCursorCheckBox.GetValue() or not self.cursorBlinkCheckBox.GetValue() :
			self.cursorBlinkRateEdit.Disable()

		self.cursorShapes = [s[0] for s in braille.CURSOR_SHAPES]
		cursorShapeChoices = [s[1] for s in braille.CURSOR_SHAPES]

		# Translators: The label for a setting in braille settings to select the cursor shape when tethered to focus.
		cursorShapeFocusLabelText = _("Cursor shape for &focus:")
		self.cursorShapeFocusList = sHelper.addLabeledControl(cursorShapeFocusLabelText, wx.Choice, choices=cursorShapeChoices)
		try:
			selection = self.cursorShapes.index(config.conf["braille"]["cursorShapeFocus"])
			self.cursorShapeFocusList.SetSelection(selection)
		except:
			pass
		if not self.showCursorCheckBox.GetValue():
			self.cursorShapeFocusList.Disable()

		# Translators: The label for a setting in braille settings to select the cursor shape when tethered to review.
		cursorShapeReviewLabelText = _("Cursor shape for &review:")
		self.cursorShapeReviewList = sHelper.addLabeledControl(cursorShapeReviewLabelText, wx.Choice, choices=cursorShapeChoices)
		try:
			selection = self.cursorShapes.index(config.conf["braille"]["cursorShapeReview"])
			self.cursorShapeReviewList.SetSelection(selection)
		except:
			pass
		if not self.showCursorCheckBox.GetValue():
			self.cursorShapeReviewList.Disable()

		# Translators: The label for a setting in braille settings to change how long a message stays on the braille display (in seconds).
		messageTimeoutText = _("Message &timeout (sec)")
		self.messageTimeoutEdit = sHelper.addLabeledControl(messageTimeoutText, nvdaControls.SelectOnFocusSpinCtrl,
			min=int(config.conf.getConfigValidationParameter(["braille", "messageTimeout"], "min")),
			max=int(config.conf.getConfigValidationParameter(["braille", "messageTimeout"], "max")),
			initial=config.conf["braille"]["messageTimeout"])

		# Translators: The label for a setting in braille settings to display a message on the braille display indefinitely.
		noMessageTimeoutLabelText = _("Show &messages indefinitely")
		self.noMessageTimeoutCheckBox = sHelper.addItem(wx.CheckBox(self, label=noMessageTimeoutLabelText))
		self.noMessageTimeoutCheckBox.Bind(wx.EVT_CHECKBOX, self.onNoMessageTimeoutChange)
		self.noMessageTimeoutCheckBox.SetValue(config.conf["braille"]["noMessageTimeout"])
		if self.noMessageTimeoutCheckBox.GetValue():
			self.messageTimeoutEdit.Disable()

		# Translators: The label for a setting in braille settings to set whether braille should be tethered to focus or review cursor.
		tetherListText = _("B&raille tethered to:")
		# Translators: The value for a setting in the braille settings, to set whether braille should be tethered to focus or review cursor.
		self.tetherValues=[("focus",_("focus")),("review",_("review"))]
		tetherChoices = [x[1] for x in self.tetherValues]
		self.tetherList = sHelper.addLabeledControl(tetherListText, wx.Choice, choices=tetherChoices)
		tetherConfig=braille.handler.tether
		selection = (x for x,y in enumerate(self.tetherValues) if y[0]==tetherConfig).next()  
		try:
			self.tetherList.SetSelection(selection)
		except:
			pass

		# Translators: The label for a setting in braille settings to read by paragraph (if it is checked, the commands to move the display by lines moves the display by paragraphs instead).
		readByParagraphText = _("Read by &paragraph")
		self.readByParagraphCheckBox = sHelper.addItem(wx.CheckBox(self, label=readByParagraphText))
		self.readByParagraphCheckBox.Value = config.conf["braille"]["readByParagraph"]

		# Translators: The label for a setting in braille settings to enable word wrap (try to avoid spliting words at the end of the braille display).
		wordWrapText = _("Avoid splitting &words when possible")
		self.wordWrapCheckBox = sHelper.addItem(wx.CheckBox(self, label=wordWrapText))
		self.wordWrapCheckBox.Value = config.conf["braille"]["wordWrap"]
		# Translators: The label for a setting in braille settings to select how the context for the focus object should be presented on a braille display.
		focusContextPresentationLabelText = _("Focus context presentation:")
		self.focusContextPresentationValues = [x[0] for x in braille.focusContextPresentations]
		focusContextPresentationChoices = [x[1] for x in braille.focusContextPresentations]
		self.focusContextPresentationList = sHelper.addLabeledControl(focusContextPresentationLabelText, wx.Choice, choices=focusContextPresentationChoices)
		try:
			index=self.focusContextPresentationValues.index(config.conf["braille"]["focusContextPresentation"])
		except:
			index=0
		self.focusContextPresentationList.SetSelection(index)

	def postInit(self):
		self.displayList.SetFocus()

	def onOk(self, evt):
		display = self.displayNames[self.displayList.GetSelection()]
		if display not in config.conf["braille"]:
			config.conf["braille"][display] = {}
		if self.possiblePorts:
			port = self.possiblePorts[self.portsList.GetSelection()][0]
			config.conf["braille"][display]["port"] = port
		if not braille.handler.setDisplayByName(display):
			gui.messageBox(_("Could not load the %s display.")%display, _("Braille Display Error"), wx.OK|wx.ICON_WARNING, self)
			return 
		config.conf["braille"]["translationTable"] = self.outTableNames[self.outTableList.GetSelection()]
		brailleInput.handler.table = self.inTables[self.inTableList.GetSelection()]
		config.conf["braille"]["expandAtCursor"] = self.expandAtCursorCheckBox.GetValue()
		config.conf["braille"]["showCursor"] = self.showCursorCheckBox.GetValue()
		config.conf["braille"]["cursorBlink"] = self.cursorBlinkCheckBox.GetValue()
		config.conf["braille"]["cursorBlinkRate"] = self.cursorBlinkRateEdit.GetValue()
		config.conf["braille"]["cursorShapeFocus"] = self.cursorShapes[self.cursorShapeFocusList.GetSelection()]
		config.conf["braille"]["cursorShapeReview"] = self.cursorShapes[self.cursorShapeReviewList.GetSelection()]
		config.conf["braille"]["noMessageTimeout"] = self.noMessageTimeoutCheckBox.GetValue()
		config.conf["braille"]["messageTimeout"] = self.messageTimeoutEdit.GetValue()
		braille.handler.tether = self.tetherValues[self.tetherList.GetSelection()][0]
		config.conf["braille"]["readByParagraph"] = self.readByParagraphCheckBox.Value
		config.conf["braille"]["wordWrap"] = self.wordWrapCheckBox.Value
		config.conf["braille"]["focusContextPresentation"] = self.focusContextPresentationValues[self.focusContextPresentationList.GetSelection()]
		super(BrailleSettingsDialog,  self).onOk(evt)

	def onDisplayNameChanged(self, evt):
		self.updatePossiblePorts()

	def updatePossiblePorts(self):
		displayName = self.displayNames[self.displayList.GetSelection()]
		displayCls = braille._getDisplayDriver(displayName)
		self.possiblePorts = []
		try:
			self.possiblePorts.extend(displayCls.getPossiblePorts().iteritems())
		except NotImplementedError:
			pass
		if self.possiblePorts:
			self.portsList.SetItems([p[1] for p in self.possiblePorts])
			try:
				selectedPort = config.conf["braille"][displayName].get("port")
				portNames = [p[0] for p in self.possiblePorts]
				selection = portNames.index(selectedPort)
			except (KeyError, ValueError):
				# Display name not in config or port not valid
				selection = 0
			self.portsList.SetSelection(selection)
		# If no port selection is possible or only automatic selection is available, disable the port selection control
		enable = len(self.possiblePorts) > 0 and not (len(self.possiblePorts) == 1 and self.possiblePorts[0][0] == "auto")
		self.portsList.Enable(enable)

	def onShowCursorChange(self, evt):
		self.cursorBlinkCheckBox.Enable(evt.IsChecked())
		self.cursorBlinkRateEdit.Enable(evt.IsChecked() and self.cursorBlinkCheckBox.GetValue())
		self.cursorShapeFocusList.Enable(evt.IsChecked())
		self.cursorShapeReviewList.Enable(evt.IsChecked())

	def onBlinkCursorChange(self, evt):
		self.cursorBlinkRateEdit.Enable(evt.IsChecked())

	def onNoMessageTimeoutChange(self, evt):
		self.messageTimeoutEdit.Enable(not evt.IsChecked())

class AddSymbolDialog(wx.Dialog):

	def __init__(self, parent):
		# Translators: This is the label for the add symbol dialog.
		super(AddSymbolDialog,self).__init__(parent, title=_("Add Symbol"))
		mainSizer=wx.BoxSizer(wx.VERTICAL)
		sHelper = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)

		# Translators: This is the label for the edit field in the add symbol dialog.
		symbolText = _("Symbol:")
		self.identifierTextCtrl = sHelper.addLabeledControl(symbolText, wx.TextCtrl)

		sHelper.addDialogDismissButtons(self.CreateButtonSizer(wx.OK | wx.CANCEL))

		mainSizer.Add(sHelper.sizer, border=guiHelper.BORDER_FOR_DIALOGS, flag=wx.ALL)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)
		self.identifierTextCtrl.SetFocus()
		self.Center(wx.BOTH | wx.CENTER_ON_SCREEN)

class SpeechSymbolsDialog(SettingsDialog):

	def __init__(self,parent):
		try:
			symbolProcessor = characterProcessing._localeSpeechSymbolProcessors.fetchLocaleData(speech.getCurrentLanguage())
		except LookupError:
			symbolProcessor = characterProcessing._localeSpeechSymbolProcessors.fetchLocaleData("en")
		self.symbolProcessor = symbolProcessor
		# Translators: This is the label for the symbol pronunciation dialog.
		# %s is replaced by the language for which symbol pronunciation is being edited.
		self.title = _("Symbol Pronunciation (%s)")%languageHandler.getLanguageDescription(self.symbolProcessor.locale)
		super(SpeechSymbolsDialog, self).__init__(parent)

	def makeSettings(self, settingsSizer):
		symbols = self.symbols = [copy.copy(symbol) for symbol in self.symbolProcessor.computedSymbols.itervalues()]
		self.pendingRemovals = {}

		sHelper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		# Translators: The label for symbols list in symbol pronunciation dialog.
		symbolsText = _("&Symbols")
		self.symbolsList = sHelper.addLabeledControl(symbolsText, nvdaControls.AutoWidthColumnListCtrl, autoSizeColumnIndex=0, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
		# Translators: The label for a column in symbols list used to identify a symbol.
		self.symbolsList.InsertColumn(0, _("Symbol"))
		self.symbolsList.InsertColumn(1, _("Replacement"))
		# Translators: The label for a column in symbols list used to identify a symbol's speech level (either none, some, most, all or character).
		self.symbolsList.InsertColumn(2, _("Level"))
		# Translators: The label for a column in symbols list which specifies when the actual symbol will be sent to the synthesizer (preserved).
		# See the "Punctuation/Symbol Pronunciation" section of the User Guide for details.
		self.symbolsList.InsertColumn(3, _("Preserve"))
		for symbol in symbols:
			item = self.symbolsList.Append((symbol.displayName,))
			self.updateListItem(item, symbol)
		self.symbolsList.Bind(wx.EVT_LIST_ITEM_FOCUSED, self.onListItemFocused)
		self.symbolsList.Bind(wx.EVT_CHAR, self.onListChar)

		# Translators: The label for the group of controls in symbol pronunciation dialog to change the pronunciation of a symbol.
		changeSymbolText = _("Change selected symbol")
		changeSymbolHelper = sHelper.addItem(guiHelper.BoxSizerHelper(self, sizer=wx.StaticBoxSizer(wx.StaticBox(self, label=changeSymbolText), wx.VERTICAL)))

		# Used to ensure that event handlers call Skip(). Not calling skip can cause focus problems for controls. More 
		# generally the advice on the wx documentation is: "In general, it is recommended to skip all non-command events
		# to allow the default handling to take place. The command events are, however, normally not skipped as usually 
		# a single command such as a button click or menu item selection must only be processed by one handler."
		def skipEventAndCall(handler):
			def wrapWithEventSkip(event):
				if event:
					event.Skip()
				return handler()
			return wrapWithEventSkip

		
		# Translators: The label for the edit field in symbol pronunciation dialog to change the replacement text of a symbol.
		replacementText = _("&Replacement")
		self.replacementEdit = changeSymbolHelper.addLabeledControl(replacementText, wx.TextCtrl)
		self.replacementEdit.Bind(wx.EVT_TEXT, skipEventAndCall(self.onSymbolEdited))

		# Translators: The label for the combo box in symbol pronunciation dialog to change the speech level of a symbol.
		levelText = _("&Level")
		symbolLevelLabels = characterProcessing.SPEECH_SYMBOL_LEVEL_LABELS
		levelChoices = [symbolLevelLabels[level] for level in characterProcessing.SPEECH_SYMBOL_LEVELS]
		self.levelList = changeSymbolHelper.addLabeledControl(levelText, wx.Choice, choices=levelChoices)
		self.levelList.Bind(wx.EVT_CHOICE, skipEventAndCall(self.onSymbolEdited))

		# Translators: The label for the combo box in symbol pronunciation dialog to change when a symbol is sent to the synthesizer.
		preserveText = _("&Send actual symbol to synthesizer")
		symbolPreserveLabels = characterProcessing.SPEECH_SYMBOL_PRESERVE_LABELS
		preserveChoices = [symbolPreserveLabels[mode] for mode in characterProcessing.SPEECH_SYMBOL_PRESERVES]
		self.preserveList = changeSymbolHelper.addLabeledControl(preserveText, wx.Choice, choices=preserveChoices)
		self.preserveList.Bind(wx.EVT_CHOICE, skipEventAndCall(self.onSymbolEdited))

		# disable the "change symbol" controls until a valid item is selected.
		self.replacementEdit.Disable()
		self.levelList.Disable()
		self.preserveList.Disable()


		bHelper = sHelper.addItem(guiHelper.ButtonHelper(orientation=wx.HORIZONTAL))
		# Translators: The label for a button in the Symbol Pronunciation dialog to add a new symbol.
		addButton = bHelper.addButton(self, label=_("&Add"))

		# Translators: The label for a button in the Symbol Pronunciation dialog to remove a symbol.
		self.removeButton = bHelper.addButton(self, label=_("Re&move"))
		self.removeButton.Disable()

		addButton.Bind(wx.EVT_BUTTON, self.OnAddClick)
		self.removeButton.Bind(wx.EVT_BUTTON, self.OnRemoveClick)

		self.editingItem = None

	def postInit(self):
		self.symbolsList.SetFocus()

	def updateListItem(self, item, symbol):
		self.symbolsList.SetStringItem(item, 1, symbol.replacement)
		self.symbolsList.SetStringItem(item, 2, characterProcessing.SPEECH_SYMBOL_LEVEL_LABELS[symbol.level])
		self.symbolsList.SetStringItem(item, 3, characterProcessing.SPEECH_SYMBOL_PRESERVE_LABELS[symbol.preserve])

	def onSymbolEdited(self):
		if self.editingItem is not None:
			# Update the symbol the user was just editing.
			item = self.editingItem
			symbol = self.symbols[item]
			symbol.replacement = self.replacementEdit.Value
			symbol.level = characterProcessing.SPEECH_SYMBOL_LEVELS[self.levelList.Selection]
			symbol.preserve = characterProcessing.SPEECH_SYMBOL_PRESERVES[self.preserveList.Selection]
			self.updateListItem(item, symbol)

	def onListItemFocused(self, evt):
		# Update the editing controls to reflect the newly selected symbol.
		item = evt.GetIndex()
		symbol = self.symbols[item]
		self.editingItem = item
		# ChangeValue and Selection property used because they do not cause EVNT_CHANGED to be fired.
		self.replacementEdit.ChangeValue(symbol.replacement)
		self.levelList.Selection = characterProcessing.SPEECH_SYMBOL_LEVELS.index(symbol.level)
		self.preserveList.Selection = characterProcessing.SPEECH_SYMBOL_PRESERVES.index(symbol.preserve)
		self.removeButton.Enabled = not self.symbolProcessor.isBuiltin(symbol.identifier)
		self.replacementEdit.Enable()
		self.levelList.Enable()
		self.preserveList.Enable()
		evt.Skip()

	def onListChar(self, evt):
		if evt.KeyCode == wx.WXK_RETURN:
			# The enter key should be propagated to the dialog and thus activate the default button,
			# but this is broken (wx ticket #3725).
			# Therefore, we must catch the enter key here.
			# Activate the OK button.
			self.ProcessEvent(wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK))
		else:
			evt.Skip()

	def OnAddClick(self, evt):
		with AddSymbolDialog(self) as entryDialog:
			if entryDialog.ShowModal() != wx.ID_OK:
				return
			identifier = entryDialog.identifierTextCtrl.GetValue()
			if not identifier:
				return
		for index, symbol in enumerate(self.symbols):
			if identifier == symbol.identifier:
				# Translators: An error reported in the Symbol Pronunciation dialog when adding a symbol that is already present.
				gui.messageBox(_('Symbol "%s" is already present.') % identifier,
					_("Error"), wx.OK | wx.ICON_ERROR)
				self.symbolsList.Select(index)
				self.symbolsList.Focus(index)
				self.symbolsList.SetFocus()
				return
		addedSymbol = characterProcessing.SpeechSymbol(identifier)
		try:
			del self.pendingRemovals[identifier]
		except KeyError:
			pass
		addedSymbol.displayName = identifier
		addedSymbol.replacement = ""
		addedSymbol.level = characterProcessing.SYMLVL_ALL
		addedSymbol.preserve = characterProcessing.SYMPRES_NEVER
		self.symbols.append(addedSymbol)
		item = self.symbolsList.Append((addedSymbol.displayName,))
		self.updateListItem(item, addedSymbol)
		self.symbolsList.Select(item)
		self.symbolsList.Focus(item)
		self.symbolsList.SetFocus()

	def OnRemoveClick(self, evt):
		index = self.symbolsList.GetFirstSelected()
		symbol = self.symbols[index]
		self.pendingRemovals[symbol.identifier] = symbol
		# Deleting from self.symbolsList focuses the next item before deleting,
		# so it must be done *before* we delete from self.symbols.
		self.symbolsList.DeleteItem(index)
		del self.symbols[index]
		index = min(index, self.symbolsList.ItemCount - 1)
		self.symbolsList.Select(index)
		self.symbolsList.Focus(index)
		# We don't get a new focus event with the new index, so set editingItem.
		self.editingItem = index
		self.symbolsList.SetFocus()

	def onOk(self, evt):
		self.onSymbolEdited()
		self.editingItem = None
		for symbol in self.pendingRemovals.itervalues():
			self.symbolProcessor.deleteSymbol(symbol)
		for symbol in self.symbols:
			if not symbol.replacement:
				continue
			self.symbolProcessor.updateSymbol(symbol)
		try:
			self.symbolProcessor.userSymbols.save()
		except IOError as e:
			log.error("Error saving user symbols info: %s" % e)
		characterProcessing._localeSpeechSymbolProcessors.invalidateLocaleData(self.symbolProcessor.locale)
		super(SpeechSymbolsDialog, self).onOk(evt)

class InputGesturesDialog(SettingsDialog):
	# Translators: The title of the Input Gestures dialog where the user can remap input gestures for commands.
	title = _("Input Gestures")

	def makeSettings(self, settingsSizer):
		filterSizer = wx.BoxSizer(wx.HORIZONTAL)
		# Translators: The label of a text field to search for gestures in the Input Gestures dialog.
		filterLabel = wx.StaticText(self, label=pgettext("inputGestures", "&Filter by:"))
		filter = wx.TextCtrl(self)
		filterSizer.Add(filterLabel, flag=wx.ALIGN_CENTER_VERTICAL)
		filterSizer.AddSpacer(guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		filterSizer.Add(filter, proportion=1)
		settingsSizer.Add(filterSizer, flag=wx.EXPAND)
		settingsSizer.AddSpacer(5)
		filter.Bind(wx.EVT_TEXT, self.onFilterChange, filter)
		
		tree = self.tree = wx.TreeCtrl(self, size=wx.Size(600, 400), style=wx.TR_HAS_BUTTONS | wx.TR_HIDE_ROOT | wx.TR_LINES_AT_ROOT | wx.TR_SINGLE )
		
		self.treeRoot = tree.AddRoot("root")
		tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.onTreeSelect)
		settingsSizer.Add(tree, proportion=1, flag=wx.EXPAND)

		self.gestures = inputCore.manager.getAllGestureMappings(obj=gui.mainFrame.prevFocus, ancestors=gui.mainFrame.prevFocusAncestors)
		self.populateTree()

		settingsSizer.AddSpacer(guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_VERTICAL)

		bHelper = guiHelper.ButtonHelper(wx.HORIZONTAL)

		# Translators: The label of a button to add a gesture in the Input Gestures dialog.
		self.addButton = bHelper.addButton(self, label=_("&Add"))
		self.addButton.Bind(wx.EVT_BUTTON, self.onAdd)
		self.addButton.Disable()

		# Translators: The label of a button to remove a gesture in the Input Gestures dialog.
		self.removeButton = bHelper.addButton(self, label=_("&Remove"))
		self.removeButton.Bind(wx.EVT_BUTTON, self.onRemove)
		self.removeButton.Disable()

		self.pendingAdds = set()
		self.pendingRemoves = set()

		settingsSizer.Add(bHelper.sizer)

	def postInit(self):
		self.tree.SetFocus()

	def populateTree(self, filter=''):
		if filter:
			#This regexp uses a positive lookahead (?=...) for every word in the filter, which just makes sure the word is present in the string to be tested without matching position or order.
			# #5060: Escape the filter text to prevent unexpected matches and regexp errors.
			# Because we're escaping, words must then be split on "\ ".
			filter = re.escape(filter)
			filterReg = re.compile(r'(?=.*?' + r')(?=.*?'.join(filter.split('\ ')) + r')', re.U|re.IGNORECASE)
		for category in sorted(self.gestures):
			treeCat = self.tree.AppendItem(self.treeRoot, category)
			commands = self.gestures[category]
			for command in sorted(commands):
				if filter and not filterReg.match(command):
					continue
				treeCom = self.tree.AppendItem(treeCat, command)
				commandInfo = commands[command]
				self.tree.SetItemPyData(treeCom, commandInfo)
				for gesture in commandInfo.gestures:
					treeGes = self.tree.AppendItem(treeCom, self._formatGesture(gesture))
					self.tree.SetItemPyData(treeGes, gesture)
			if not self.tree.ItemHasChildren(treeCat):
				self.tree.Delete(treeCat)
			elif filter:
				self.tree.Expand(treeCat)

	def onFilterChange(self, evt):
		filter=evt.GetEventObject().GetValue()
		self.tree.DeleteChildren(self.treeRoot)
		self.populateTree(filter)

	def _formatGesture(self, identifier):
		try:
			source, main = inputCore.getDisplayTextForGestureIdentifier(identifier)
			# Translators: Describes a gesture in the Input Gestures dialog.
			# {main} is replaced with the main part of the gesture; e.g. alt+tab.
			# {source} is replaced with the gesture's source; e.g. laptop keyboard.
			return _("{main} ({source})").format(main=main, source=source)
		except LookupError:
			return identifier

	def onTreeSelect(self, evt):
		item = self.tree.Selection
		data = self.tree.GetItemPyData(item)
		isCommand = isinstance(data, inputCore.AllGesturesScriptInfo)
		isGesture = isinstance(data, basestring)
		self.addButton.Enabled = isCommand or isGesture
		self.removeButton.Enabled = isGesture

	def onAdd(self, evt):
		if inputCore.manager._captureFunc:
			return

		treeCom = self.tree.Selection
		scriptInfo = self.tree.GetItemPyData(treeCom)
		if not isinstance(scriptInfo, inputCore.AllGesturesScriptInfo):
			treeCom = self.tree.GetItemParent(treeCom)
			scriptInfo = self.tree.GetItemPyData(treeCom)
		# Translators: The prompt to enter a gesture in the Input Gestures dialog.
		treeGes = self.tree.AppendItem(treeCom, _("Enter input gesture:"))
		self.tree.SelectItem(treeGes)
		self.tree.SetFocus()

		def addGestureCaptor(gesture):
			if gesture.isModifier:
				return False
			inputCore.manager._captureFunc = None
			wx.CallAfter(self._addCaptured, treeGes, scriptInfo, gesture)
			return False
		inputCore.manager._captureFunc = addGestureCaptor

	def _addCaptured(self, treeGes, scriptInfo, gesture):
		gids = gesture.normalizedIdentifiers
		if len(gids) > 1:
			# Multiple choices. Present them in a pop-up menu.
			menu = wx.Menu()
			for gid in gids:
				disp = self._formatGesture(gid)
				item = menu.Append(wx.ID_ANY, disp)
				self.Bind(wx.EVT_MENU,
					lambda evt, gid=gid, disp=disp: self._addChoice(treeGes, scriptInfo, gid, disp),
					item)
			self.PopupMenu(menu)
			if not self.tree.GetItemPyData(treeGes):
				# No item was selected, so use the first.
				self._addChoice(treeGes, scriptInfo, gids[0],
					self._formatGesture(gids[0]))
			menu.Destroy()
		else:
			self._addChoice(treeGes, scriptInfo, gids[0],
				self._formatGesture(gids[0]))

	def _addChoice(self, treeGes, scriptInfo, gid, disp):
		entry = (gid, scriptInfo.moduleName, scriptInfo.className, scriptInfo.scriptName)
		try:
			# If this was just removed, just undo it.
			self.pendingRemoves.remove(entry)
		except KeyError:
			self.pendingAdds.add(entry)
		self.tree.SetItemText(treeGes, disp)
		self.tree.SetItemPyData(treeGes, gid)
		scriptInfo.gestures.append(gid)
		self.onTreeSelect(None)

	def onRemove(self, evt):
		treeGes = self.tree.Selection
		gesture = self.tree.GetItemPyData(treeGes)
		treeCom = self.tree.GetItemParent(treeGes)
		scriptInfo = self.tree.GetItemPyData(treeCom)
		entry = (gesture, scriptInfo.moduleName, scriptInfo.className, scriptInfo.scriptName)
		try:
			# If this was just added, just undo it.
			self.pendingAdds.remove(entry)
		except KeyError:
			self.pendingRemoves.add(entry)
		self.tree.Delete(treeGes)
		scriptInfo.gestures.remove(gesture)
		self.tree.SetFocus()

	def onOk(self, evt):
		for gesture, module, className, scriptName in self.pendingRemoves:
			try:
				inputCore.manager.userGestureMap.remove(gesture, module, className, scriptName)
			except ValueError:
				# The user wants to unbind a gesture they didn't define.
				inputCore.manager.userGestureMap.add(gesture, module, className, None)

		for gesture, module, className, scriptName in self.pendingAdds:
			try:
				# The user might have unbound this gesture,
				# so remove this override first.
				inputCore.manager.userGestureMap.remove(gesture, module, className, None)
			except ValueError:
				pass
			inputCore.manager.userGestureMap.add(gesture, module, className, scriptName)

		if self.pendingAdds or self.pendingRemoves:
			# Only save if there is something to save.
			try:
				inputCore.manager.userGestureMap.save()
			except:
				log.debugWarning("", exc_info=True)
				# Translators: An error displayed when saving user defined input gestures fails.
				gui.messageBox(_("Error saving user defined gestures - probably read only file system."),
					_("Error"), wx.OK | wx.ICON_ERROR)

		super(InputGesturesDialog, self).onOk(evt)

class TouchInteractionDialog(SettingsDialog):
	# Translators: This is the label for the touch interaction settings dialog.
	title = _("Touch Interaction")

	def makeSettings(self, settingsSizer):
		# Translators: This is the label for a checkbox in the
		# touch interaction settings dialog.
		self.touchTypingCheckBox=wx.CheckBox(self,wx.NewId(),label=_("&Touch typing mode"))
		self.touchTypingCheckBox.SetValue(config.conf["touch"]["touchTyping"])
		settingsSizer.Add(self.touchTypingCheckBox,border=10,flag=wx.BOTTOM)

	def postInit(self):
		self.touchTypingCheckBox.SetFocus()

	def onOk(self,evt):
		config.conf["touch"]["touchTyping"]=self.touchTypingCheckBox.IsChecked()
		super(TouchInteractionDialog, self).onOk(evt)
