#  ___________________________________________________________________________
#
#  Pyomo: Python Optimization Modeling Objects
#  Copyright 2017 National Technology and Engineering Solutions of Sandia, LLC
#  Under the terms of Contract DE-NA0003525 with National Technology and 
#  Engineering Solutions of Sandia, LLC, the U.S. Government retains certain 
#  rights in this software.
#  This software is distributed under the 3-clause BSD License.
#  ___________________________________________________________________________
#
# Test the Pyomo command-line interface
#

from itertools import zip_longest
import json
import re
import os
import sys
from os.path import abspath, dirname, join
currdir = dirname(abspath(__file__))+os.sep

from filecmp import cmp
import subprocess
import pyomo.common.unittest as unittest

from pyomo.common.dependencies import yaml_available
from pyomo.common.tee import capture_output
import pyomo.core
import pyomo.scripting.pyomo_main as main
from pyomo.opt import check_available_solvers

from io import StringIO

if os.path.exists(sys.exec_prefix+os.sep+'bin'+os.sep+'coverage'):
    executable=sys.exec_prefix+os.sep+'bin'+os.sep+'coverage -x '
else:
    executable=sys.executable

def filter_fn(line):
    tmp = line.strip()
    return tmp.startswith('Disjunct') or tmp.startswith('DEPRECATION') or tmp.startswith('DiffSet') or line.startswith('    ') or tmp.startswith("Differential") or tmp.startswith("DerivativeVar") or tmp.startswith("InputVar") or tmp.startswith('StateVar') or tmp.startswith('Complementarity')


_diff_tol = 1e-6

solvers = None
class BaseTester(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        global solvers
        import pyomo.environ
        solvers = check_available_solvers('glpk')

    def pyomo(self, cmd, **kwds):
        if 'root' in kwds:
            OUTPUT=kwds['root']+'.out'
            results=kwds['root']+'.jsn'
            self.ofile = OUTPUT
        else:
            OUTPUT=StringIO()
            results='results.jsn'
        with capture_output(OUTPUT):
            os.chdir(currdir)
            if type(cmd) is list:
                output = main.main(['solve', '--solver=glpk', '--results-format=json', '--save-results=%s' % results] + cmd)
            elif cmd.endswith('json') or cmd.endswith('yaml'):
                output = main.main(['solve', '--results-format=json', '--save-results=%s' % results] + [cmd])
            else:
                args=re.split('[ ]+',cmd)
                output = main.main(['solve', '--solver=glpk', '--results-format=json', '--save-results=%s' % results] + list(args))
        if not 'root' in kwds:
            return OUTPUT.getvalue()
        return output

    def setUp(self):
        self.ofile = None
        if not 'glpk' in solvers:
            self.skipTest("GLPK is not installed")

    def tearDown(self):
        return
        if self.ofile and os.path.exists(self.ofile):
            return
            os.remove(self.ofile)
        if os.path.exists(join(currdir, 'results.jsn')):
            return
            os.remove(join(currdir, 'results.jsn'))

    def run_pyomo(self, cmd, root=None):
        cmd = ('pyomo solve --solver=glpk --results-format=json ' \
              '--save-results=%s.jsn %s' % (root, cmd)).split(' ')
        with open(join(root, '.out'), 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=f)
        return result


class TestJson(BaseTester):

    def compare_json(self, file1, file2):
        with open(file1, 'r') as f1, open(file2, 'r') as f2:
            f1_contents = json.load(f1)
            f2_contents = json.load(f2)
            self.assertStructuredAlmostEqual(f2_contents,
                                             f1_contents,
                                             abstol=_diff_tol,
                                             allow_second_superset=True)
    def filter_items(self, items):
        filtered = []
        for i in items:
            if not (i.startswith('/') or i.startswith(":\\", 1)):
                try:
                    filtered.append(float(i))
                except:
                    filtered.append(i)
        return filtered

    def compare_files(self, file1, file2):
        try:
            self.assertTrue(cmp(file1, file2),
                        msg="Files %s and %s differ" % (file1, file2))
        except:
            with open(file1, 'r') as f1, open(file2, 'r') as f2:
                f1_contents = f1.read().strip().split('\n')
                f2_contents = f2.read().strip().split('\n')
                f1_filtered = []
                f2_filtered = []
                for item1, item2 in zip_longest(f1_contents, f2_contents):
                    if not item1.startswith('['):
                        items1 = item1.strip().split()
                        items2 = item2.strip().split()
                        f1_filtered.append(self.filter_items(items1))
                        f2_filtered.append(self.filter_items(items2))
                self.assertStructuredAlmostEqual(f2_filtered, f1_filtered,
                                                 abstol=1e-6,
                                                 allow_second_superset=True)

    def test1_simple_pyomo_execution(self):
        # Simple execution of 'pyomo'
        self.pyomo([join(currdir, 'pmedian.py'),join(currdir, 'pmedian.dat')], root=join(currdir, 'test1'))
        self.compare_json(join(currdir, 'test1.jsn'), join(currdir, 'test1.txt'))
        os.remove(os.path.join(currdir, 'test1.out'))

    def test1a_simple_pyomo_execution(self):
        # Simple execution of 'pyomo' in a subprocess
        files = os.path.join(currdir, 'pmedian.py') + ' ' + os.path.join(currdir, 'pmedian.dat')
        self.run_pyomo(files, root=os.path.join(currdir, 'test1a'))
        self.compare_json(join(currdir, 'test1a.jsn'), join(currdir, 'test1.txt'))

    def test1b_simple_pyomo_execution(self):
        # Simple execution of 'pyomo' with a configuration file
        self.pyomo(join(currdir, 'test1b.json'), root=join(currdir, 'test1'))
        self.compare_json(join(currdir, 'test1.jsn'), join(currdir, 'test1.txt'))
        os.remove(os.path.join(currdir, 'test1.out'))

    def test2_bad_model_name(self):
        # Run pyomo with bad --model-name option value
        self.pyomo('--model-name=dummy pmedian.py pmedian.dat', root=join(currdir, 'test2'))
        self.compare_files(join(currdir, "test2.out"), join(currdir, "test2.txt"))

    def test2b_bad_model_name(self):
        # Run pyomo with bad --model-name option value (configfile)
        self.pyomo(join(currdir, 'test2b.json'), root=join(currdir, 'test2'))
        self.compare_files(join(currdir, "test2.out"), join(currdir, "test2.txt"))

    def test3_missing_model_object(self):
        # Run pyomo with model that does not define model object
        self.pyomo('pmedian1.py pmedian.dat', root=join(currdir, 'test3'))
        self.compare_json(join(currdir, "test3.jsn"), join(currdir, "test1.txt"))
        os.remove(os.path.join(currdir, 'test3.out'))

    def test4_valid_modelname_option(self):
        # Run pyomo with good --model-name option value
        self.pyomo('--model-name=MODEL '+join(currdir, 'pmedian1.py pmedian.dat'), root=join(currdir, 'test4'))
        self.compare_json(join(currdir, "test4.jsn"), join(currdir, "test1.txt"))
        os.remove(os.path.join(currdir, 'test4.out'))

    def test4b_valid_modelname_option(self):
        # Run pyomo with good 'object name' option value (configfile)
        self.pyomo(join(currdir, 'test4b.json'), root=join(currdir, 'test4b'))
        self.compare_json(join(currdir, "test4b.jsn"), join(currdir, "test1.txt"))
        os.remove(os.path.join(currdir, 'test4b.out'))

    def test5_create_model_fcn(self):
        #"""Run pyomo with create_model function"""
        self.pyomo('pmedian2.py pmedian.dat', root=join(currdir, 'test5'))
        self.compare_files(join(currdir, "test5.out"), join(currdir, "test5.txt"))
        os.remove(os.path.join(currdir, 'test5.jsn'))

    def test5b_create_model_fcn(self):
        # Run pyomo with create_model function (configfile)
        self.pyomo(join(currdir, 'test5b.json'), root=join(currdir, 'test5'))
        self.compare_files(join(currdir, "test5.out"), join(currdir, "test5.txt"))
        os.remove(os.path.join(currdir, 'test5.jsn'))

    def test8_instanceonly_option(self):
        #"""Run pyomo with --instance-only option"""
        output = self.pyomo('--instance-only pmedian.py pmedian.dat', root=join(currdir, 'test8'))
        self.assertEqual(type(output.retval.instance), pyomo.core.ConcreteModel)
        # Check that the results file was NOT created
        self.assertRaises(OSError, lambda: os.remove(join(currdir, 'test8.jsn')))
        os.remove(os.path.join(currdir, 'test8.out'))

    def test8b_instanceonly_option(self):
        # Run pyomo with --instance-only option (configfile)
        output = self.pyomo(join(currdir, 'test8b.json'), root=join(currdir, 'test8'))
        self.assertEqual(type(output.retval.instance), pyomo.core.ConcreteModel)
        # Check that the results file was NOT created
        self.assertRaises(OSError, lambda: os.remove(join(currdir, 'test8.jsn')))
        os.remove(os.path.join(currdir, 'test8.out'))

    def test9_disablegc_option(self):
        #"""Run pyomo with --disable-gc option"""
        output = self.pyomo('--disable-gc pmedian.py pmedian.dat', root=join(currdir, 'test9'))
        self.assertEqual(type(output.retval.instance), pyomo.core.ConcreteModel)
        os.remove(os.path.join(currdir, 'test9.jsn'))
        os.remove(os.path.join(currdir, 'test9.out'))

    def test9b_disablegc_option(self):
        # Run pyomo with --disable-gc option (configfile)
        output = self.pyomo(join(currdir, 'test9b.json'), root=join(currdir, 'test9'))
        self.assertEqual(type(output.retval.instance), pyomo.core.ConcreteModel)
        os.remove(os.path.join(currdir, 'test9.jsn'))
        os.remove(os.path.join(currdir, 'test9.out'))

    def test12_output_option(self):
        #"""Run pyomo with --output option"""
        self.pyomo('--logfile=%s pmedian.py pmedian.dat' % (join(currdir, 'test12.log')), root=join(currdir, 'test12'))
        self.compare_json(join(currdir, "test12.jsn"), join(currdir, "test12.txt"))
        os.remove(os.path.join(currdir, 'test12.log'))
        os.remove(os.path.join(currdir, 'test12.out'))

    def test12b_output_option(self):
        # Run pyomo with --output option (configfile)
        self.pyomo(join(currdir, 'test12b.json'), root=join(currdir, 'test12'))
        self.compare_json(join(currdir, "test12.jsn"), join(currdir, "test12.txt"))
        os.remove('test12b.log')
        os.remove(os.path.join(currdir, 'test12.out'))

    def test14_concrete_model_with_constraintlist(self):
        # Simple execution of 'pyomo' with a concrete model and constraint lists
        self.pyomo('pmedian4.py', root=join(currdir, 'test14'))
        self.compare_json(join(currdir, "test14.jsn"), join(currdir, "test14.txt"))
        os.remove(os.path.join(currdir, 'test14.out'))

    def test14b_concrete_model_with_constraintlist(self):
        # Simple execution of 'pyomo' with a concrete model and constraint lists (configfile)
        self.pyomo('pmedian4.py', root=join(currdir, 'test14'))
        self.compare_json(join(currdir, "test14.jsn"), join(currdir, "test14.txt"))
        os.remove(os.path.join(currdir, 'test14.out'))

    def test15_simple_pyomo_execution(self):
        # Simple execution of 'pyomo' with options
        self.pyomo(['--solver-options="mipgap=0.02 cuts="', join(currdir, 'pmedian.py'), 'pmedian.dat'], root=join(currdir, 'test15'))
        self.compare_json(join(currdir, "test15.jsn"), join(currdir, "test1.txt"))
        os.remove(os.path.join(currdir, 'test15.out'))

    def test15b_simple_pyomo_execution(self):
        # Simple execution of 'pyomo' with options
        self.pyomo(join(currdir, 'test15b.json'), root=join(currdir, 'test15b'))
        self.compare_json(join(currdir, "test15b.jsn"), join(currdir, "test1.txt"))
        os.remove(os.path.join(currdir, 'test15b.out'))

    def test15c_simple_pyomo_execution(self):
        # Simple execution of 'pyomo' with options
        self.pyomo(join(currdir, 'test15c.json'), root=join(currdir, 'test15c'))
        self.compare_json(join(currdir, "test15c.jsn"), join(currdir, "test1.txt"))
        os.remove(os.path.join(currdir, 'test15c.out'))


@unittest.skipIf(not yaml_available, "YAML not available available")
class TestWithYaml(BaseTester):

    def compare_json(self, file1, file2):
        with open(file1, 'r') as f1, open(file2, 'r') as f2:
            f1_contents = json.load(f1)
            f2_contents = json.load(f2)
            self.assertStructuredAlmostEqual(f2_contents,
                                             f1_contents,
                                             abstol=_diff_tol,
                                             allow_second_superset=True)

    def test15b_simple_pyomo_execution(self):
        # Simple execution of 'pyomo' with options
        self.pyomo(join(currdir, 'test15b.yaml'), root=join(currdir, 'test15b'))
        self.compare_json(join(currdir, "test15b.jsn"), join(currdir, "test1.txt"))
        os.remove(os.path.join(currdir, 'test15b.out'))

    def test15c_simple_pyomo_execution(self):
        # Simple execution of 'pyomo' with options
        self.pyomo(join(currdir, 'test15c.yaml'), root=join(currdir, 'test15c'))
        self.compare_json(join(currdir, "test15c.jsn"), join(currdir, "test1.txt"))
        os.remove(os.path.join(currdir, 'test15c.out'))


if __name__ == "__main__":
    unittest.main()
