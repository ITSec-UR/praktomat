# -*- coding: utf-8 -*-

import os, re
from pipes import quote

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.html import escape
from checker.models import Checker, CheckerFileField, CheckerResult, execute_arglist, truncated_log
from utilities.file_operations import *

class ScriptChecker(Checker):

	name = models.CharField(max_length=100, default="Externen Tutor ausführen", help_text=_("Name to be displayed on the solution detail page."))
	shell_script = CheckerFileField(help_text=_("The shell script whose output for the given input file is compared to the given output file."))
	remove = models.CharField(max_length=5000, blank=True, help_text=_("Regular expression describing passages to be removed from the output."))
	returns_html = models.BooleanField(default= False, help_text=_("If the script doesn't return HTML it will be enclosed in &lt; pre &gt; tags."))

	
	def title(self):
		""" Returns the title for this checker category. """
		return self.name
	
	@staticmethod
	def description():
		""" Returns a description for this Checker. """
		return u"Diese Prüfung wird bestanden, wenn das externe Programm keinen Fehlercode liefert."
	

	def run(self, env):
		""" Runs tests in a special environment. Here's the actual work. 
		This runs the check in the environment ENV, returning a CheckerResult. """

		# Setup
		replace = [("PROGRAM",env.program())] if env.program() else []
		replace +=[("JAVA",settings.JVM_SECURE)]
		copy_file_to_directory(self.shell_script.path, env.tmpdir(), replace=replace)
		os.chmod(env.tmpdir()+'/'+os.path.basename(self.shell_script.name),0750)
		
		# Run the tests -- execute dumped shell script 'script.sh'

		filenames = [quote(name) for (name,content) in env.sources()]
		args = [env.tmpdir()+'/'+os.path.basename(self.shell_script.name)] + filenames

		environ = {}
		environ['USER'] = str(env.user().id)
		environ['HOME'] = env.tmpdir()
		environ['JAVA'] = settings.JVM

		[output, error, exitcode,timed_out] = execute_arglist(args, working_directory=env.tmpdir(), environment_variables=environ,timeout=settings.TEST_TIMEOUT,fileseeklimit=settings.TEST_MAXFILESIZE)

		result = CheckerResult(checker=self)
		(output,truncated) = truncated_log(output)

		if self.remove:
			output = re.sub(self.remove, "", output)
		if not self.returns_html or truncated:
			output = '<pre>' + escape(output) + '</pre>'

		result.set_log(output,timed_out=timed_out,truncated=truncated)
		result.set_passed(not exitcode and not timed_out and not truncated)
		
		return result
	
from checker.admin import	CheckerInline

class ScriptCheckerInline(CheckerInline):
	model = ScriptChecker

