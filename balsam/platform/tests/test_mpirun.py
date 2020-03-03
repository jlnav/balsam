import os
import re
import logging
import shutil
import unittest
import time
from balsam.platform.mpirun import MPIRun


class MpirunTestMixin(object):
    def assertInPath(self, exe):
        which_exe = shutil.which(exe)
        self.assertTrue(which_exe is not None, f"'{exe}' not in PATH")

    def test_start(self):
        self.assertInPath(self.mpirun.launch_command)

        self.mpirun.start(os.getcwd(),self.script_output)

        retval = self.mpirun.wait()
        self.assertIsInstance(retval,int)
        self.assertEqual(retval,0)

        ranks,size,reduce = self.parse_output(self.script_output)

        self.assertEqual(ranks,self.ranks)
        self.assertEqual(size,self.ranks)

        self.assertEqual(reduce,self.ranks*self.reduce_val)


    def test_poll(self):
        self.assertInPath(self.mpirun.launch_command)

        self.mpirun.start(os.getcwd(), self.script_output)

        retval = self.mpirun.poll()
        counter = 0
        while retval is None:
            time.sleep(1)
            retval = self.mpirun.poll()
            counter += 1
            if counter > 100:
                break

        self.assertLessEqual(counter,self.sleep_sec+1)

    def test_terminate(self):
        self.assertInPath(self.mpirun.launch_command)

        self.mpirun.start(os.getcwd(), self.script_output)
        start = time.time()
        self.mpirun.terminate()
        retval = self.mpirun.wait()
        end = time.time()
        self.assertLessEqual(end-start,self.sleep_sec)

    def test_kill(self):
        self.assertInPath(self.mpirun.launch_command)

        self.mpirun.start(os.getcwd(), self.script_output)
        start = time.time()
        self.mpirun.kill()
        retval = self.mpirun.wait()
        end = time.time()
        self.assertLessEqual(end-start,self.sleep_sec)

    def test_wait(self):
        self.assertInPath(self.mpirun.launch_command)

        start = time.time()
        self.mpirun.start(os.getcwd(), self.script_output)
        retval = self.mpirun.wait()
        end = time.time()
        self.assertGreaterEqual(end - start, self.sleep_sec)


class MPIRunTest(MpirunTestMixin, unittest.TestCase):
    reduce_val = 5
    sleep_sec = 2
    test_script = """from mpi4py import MPI
import time
c = MPI.COMM_WORLD
print('rank',c.Get_rank(),'of',c.Get_size())
x = {0}
y = c.allreduce(x,MPI.SUM)
print('reduce ',y)
time.sleep({1})
""".format(reduce_val,sleep_sec)
    script_fn = "temp.py"
    script_output = "temp.txt"

    ranks = 4
    ranks_per_node = 2

    def setUp(self):
        with open(self.script_fn,'w') as file:
            file.write(self.test_script)
        app_args = ['python',self.script_fn]
        node_list = ['nodeA','nodeB']
        num_ranks = self.ranks
        ranks_per_node = self.ranks_per_node
        env = os.environ
        self.mpirun = MPIRun(app_args,node_list,num_ranks,ranks_per_node,env=env)
        self.mpirun.get_launch_args = lambda: ['-n',num_ranks]

    @staticmethod
    def parse_output(output_fn):

        ranks = []
        sizes = []
        with open(output_fn) as file:
            for line in file:
                if line.startswith('rank'):
                    rank,size = re.findall('\d+',line)
                    ranks.append(int(rank))
                    sizes.append(int(size))
                elif line.startswith('reduce'):
                    reduce = re.findall('\d+',line)

        return len(set(ranks)),tuple(set(sizes))[0],int(reduce[0])

    def tearDown(self):
        os.remove(self.script_fn)
        os.remove(self.script_output)




if __name__ == "__main__":
    import logging

    logging.basicConfig()
    unittest.main()
