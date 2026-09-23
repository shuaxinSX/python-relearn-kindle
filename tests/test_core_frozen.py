"""Core V1 lesson freeze: any byte change to the 16 core lesson YAMLs fails loudly.

This is a NEW pin taken at the M0-era baseline. It is independent of
docs/v1-review.json (which must never be edited to make a red test green).
Only update these pins after a genuine human re-review; never recompute
them just to silence this test.
"""
import hashlib
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
# Pinned 2026-09-23 from the untouched core lesson files.
PINS={
    'run-and-bindings': '226c5aa2c780c7c64482dac967ea5b5f3781b9814c9621b5df93c21c1c0555d3',
    'types-and-none': '672b4618a0eca38be4b560270a699656fd5775c1cae1ebabf0dd71bb1d10ecda',
    'strings': '3c6f97773393ded5e4fe6d0f0b2671a92b515d3aa39f2eaa50a7825e68543162',
    'conditions': '04881e9822c162024637531ab0e25ace3bf22cc97cb76bf954e0ac059b88ea28',
    'loops': '7740884642ec55039f20483e53ac1553de3828b6549cc7dd5096501bcf75354c',
    'lists-tuples': '86f3eaecc6982e279a7a9b7fec325e02bb1af3e4aaf2d3dd42bf5c06a2e6d206',
    'dicts': 'aac3a9ee81a7c11b62b389095bf91914e76f03ee19ef1542b755b208a12153b1',
    'sets': '38626cf237b50f02bd47a57eac641bb9c049e233a01ec38954de91b02430ce12',
    'functions': '5caad5d64df90b45ab5be0d179aebbc9f487845504f238859bf0e032fa6ce65c',
    'scope-defaults': '457fa2fc54968882aa3e37707c991532a7df503031ccf203640917efdebd80f2',
    'alias-copy': '4c1f2de49ae5b576a44d3874b9e36d135097f97f032b56bab28de4b931a301d7',
    'comprehensions-sort': '71067b2260fa53b495eab0cc88b421d141f2277daa3b7146373a66acaafb870d',
    'exceptions': '7fdaa56290f50defbb91d4f3c8466134a1abe8961b6b6e950f211c4f7b3dc313',
    'paths-text': '911d65a4ad84d317c053e7aed9cc761763ef5993f2509b085f48ab77f4ff05f2',
    'modules-venv': '05ae0de060095d353c12ca26b45290e1fe55f57326c429aa3d2bd62ce0b96971',
    'tests-boundaries': '587b39c0383eb3b6f273826504e6b75cb8395f2eaf7c954430bb1c93261bca54',
}

class TestCoreFrozen(unittest.TestCase):
    def test_core_lesson_yaml_bytes_unchanged(self):
        self.assertEqual(len(PINS),16)
        for lid,digest in PINS.items():
            with self.subTest(lesson=lid):
                actual=hashlib.sha256((ROOT/'content/lessons'/f'{lid}.yaml').read_bytes()).hexdigest()
                self.assertEqual(actual,digest,'核心课 YAML 被修改：须人工复审并有意更新本 pin，禁止为消红而重算')

if __name__=='__main__':unittest.main()
