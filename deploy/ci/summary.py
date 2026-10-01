#!/usr/bin/python3
##### Summarise PHPUnit and QUnit results as Markdown for the job summary

import os
import re
import xml.etree.ElementTree as ET

print('## Test results\n')
print('| Suite | Result |')
print('|---|---|')

junit = 'build/logs/junit.xml'
if os.path.exists(junit):
  suite = ET.parse(junit).getroot()
  if suite.tag == 'testsuites' and len(suite):
    suite = suite[0]
  tests = int(suite.get('tests', 0))
  failed = int(suite.get('failures', 0)) + int(suite.get('errors', 0))
  skipped = int(suite.get('skipped', 0))
  print('| PHPUnit | %d tests, %d failed, %d skipped |' % (tests, failed, skipped))
else:
  print('| PHPUnit | not run |')

qunit = 'build/logs/qunit.log'
match = None
if os.path.exists(qunit):
  match = re.search(r'(\d+) assertions of (\d+) passed, (\d+) failed', open(qunit).read())
if match:
  print('| QUnit | %s of %s assertions passed, %s failed |' % match.groups())
else:
  print('| QUnit | not run |')
