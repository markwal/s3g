import os
import sys
lib_path = os.path.abspath('../')
sys.path.append(lib_path)

import unittest
import tempfile

import makerbot_driver

class RpmProcessor(unittest.TestCase):

  def setUp(self):
    self.rp = makerbot_driver.GcodeProcessors.RpmProcessor()
    
  def tearDown(self):
    self.rp = None

  def test_transform_m101_non_m101_command(self):
    input_string = 'G1;M101\n'
    expected_string = 'G1;M101\n'
    got_string = self.rp._transform_m101(input_string)
    self.assertEqual(expected_string, got_string)

  def test_transform_m101(self):
    input_string = 'M101\n'
    expected_string = ''
    got_string = self.rp._transform_m101(input_string)
    self.assertEqual(expected_string, got_string)

  def test_transform_m102_non_m102_command(self):
    input_string = 'G1;M102\n'
    expected_string = 'G1;M102\n'
    got_string = self.rp._transform_m102(input_string)
    self.assertEqual(expected_string, got_string)

  def test_transform_m102(self):
    input_string = 'M102\n'
    expected_string = ''
    got_string = self.rp._transform_m102(input_string)
    self.assertEqual(expected_string, got_string)

  def test_transform_m103_non_m103_command(self):
    input_string = 'G1;M103\n'
    expected_string = 'G1;M103\n'
    got_string = self.rp._transform_m103(input_string)
    self.assertEqual(expected_string, got_string)

  def test_transform_m103(self):
    input_string = 'M103\n'
    expected_string = ''
    got_string = self.rp._transform_m103(input_string)
    self.assertEqual(expected_string, got_string)

  def test_transform_m108(self):
    input_output_dict = {
        'M108\n'    :   '',
        'M108 R25.1\n'    :   '',
        'M108;comment\n'  :   '',
        'M108 T0\n'       :   'M135 T0\n',
        'M108 T0 R25.1\n' :   'M135 T0\n',
        'M108 T0 R25.1;superCOMMENT\n'  : 'M135 T0; superCOMMENT\n',
        'M108 (heres a comment) T0\n'   : 'M135 T0; heres a comment\n',
        'M108 (heres a comment) T0;heres another comment\n'   :   'M135 T0; heres another commentheres a comment\n',
        }
    for key in input_output_dict:
      self.assertEqual(input_output_dict[key], self.rp._transform_m108(key))

  def test_process_file_can_proces_parsable_file(self):
    #Make input temp file
    gcodes = ["M103\n","M101\n","M108 R2.51 T0\n","M105\n"]
    got_output = self.rp.process_gcode(gcodes)
    expected_output = ["M135 T0\n","M105\n"]
    self.assertEqual(expected_output, got_output)

if __name__ == '__main__':
  unittest.main()