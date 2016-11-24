#!/usr/bin/env python
from __future__ import print_function

import json
import os
import sys

from unittest import TestCase
import pandas as pd

from utils import TemporaryDirectory, Move, TestData, touch, TemporaryFile
from utils import run_task, run_tasks, check_status

from dammit.tasks.hmmer import get_hmmscan_task as hmmscan_task
from dammit.tasks.hmmer import get_hmmpress_task as hmmpress_task
from dammit.fileio.hmmer import HMMerParser
from dammit.meta import get_config

class TestHMMERTasks(TestCase):

    @classmethod
    def setup_class(cls):
        cfg, _ = get_config()
        cls.hmmscan_cfg = cfg['hmmer']['hmmscan']
        cls.hmmpress_cfg = cfg['hmmer']['hmmpress']
        cls.extensions = ['.h3f', '.h3i', '.h3m', '.h3p']

    def test_hmmpress_task(self):
        with TemporaryDirectory() as td:
            with Move(td):
                with TestData('test-profile.hmm', td) as tf:
                    task = hmmpress_task(tf, self.hmmpress_cfg)
                    run_tasks([task], ['run'])
                    status = check_status(task)
                    print(os.listdir(td), file=sys.stderr)
                    
                    for ext in self.extensions:
                        self.assertTrue(os.path.isfile(tf + ext))

                    self.assertEquals(status.status, 'up-to-date')
    
    def test_hmmpress_task_existing(self):
        with TemporaryDirectory() as td:
            with Move(td):
                with TestData('test-profile.hmm', td) as tf:
                    for ext in self.extensions:
                        touch(tf + ext)

                    task = hmmpress_task(tf, self.hmmpress_cfg)
                    run_tasks([task], ['run'])
                    print(os.listdir(td), file=sys.stderr)
                    print(task, file=sys.stderr)
                    status = check_status(task)
                    
                    self.assertEquals(status.status, 'up-to-date')

    def test_hmmscan_task(self):
        with TemporaryDirectory() as td:
            with Move(td):
                with TestData('test-protein.fa', td) as prot, \
                     TestData('test-profile.hmm', td) as hmm, \
                     TemporaryFile(td) as out:
                        
                    db_task = hmmpress_task(hmm, self.hmmpress_cfg)
                    aln_task = hmmscan_task(prot, out, hmm, 1.0, 1)

                    run_tasks([db_task, aln_task], ['run'])
                    print(os.listdir(td), file=sys.stderr)
                    aln = open(out).read()
                    print(aln)

                    self.assertEquals(aln.count('accession'), 2)
                    self.assertIn('i-Evalue', aln)

    def test_hmmscan_task_multithreaded(self):
        with TemporaryDirectory() as td:
            with Move(td):
                with TestData('20aa-alitest.fa', td) as prot, \
                     TestData('20aa.hmm', td) as hmm, \
                     TemporaryFile(td) as out_single,\
                     TemporaryFile(td) as out_multi:
                    
                    for n_threads in (2,3,4,5):
                        db_task = hmmpress_task(hmm, self.hmmpress_cfg)
                        aln_task_single = hmmscan_task(prot, out_single, 
                                                   hmm, 1.0, 1)
                        aln_task_multi = hmmscan_task(prot, out_multi,
                                                  hmm, 1.0, n_threads)
                        run_tasks([db_task, aln_task_single], ['run'])
                        run_tasks([aln_task_multi], ['run'])
                        print(os.listdir(td), file=sys.stderr)

                        print(open(out_single).read())
                        alns_single = pd.concat(HMMerParser(out_single))
                        alns_multi = pd.concat(HMMerParser(out_multi))

                        self.assertTrue(all(alns_single['domain_i_evalue'].sort_values() == \
                                            alns_multi['domain_i_evalue'].sort_values()))

