import bisect
import pathlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from scripts.transcription_notation import generate_score


class NotationTests(unittest.TestCase):
    def fixture(self):
        module = SimpleNamespace()
        module._quantize_time = lambda t, grid: bisect.bisect_left([(a+b)/2 for a,b in zip(grid,grid[1:])],t)
        def fill(rows, grid, **kwargs):
            for a,b,v in rows:
                if module._quantize_time(b,grid)<=module._quantize_time(a,grid):
                    raise ValueError(f'Interval {a:.6f}-{b:.6f} ({v}) is shorter than the ABC subbeat grid')
            return list(rows)
        module._fill_intervals = fill
        def generate(rows):
            kept=module._fill_intervals(rows,[0,.125,.25,.375,.5],default='N',dtype='<U64')
            return 'validated ABC',SimpleNamespace(diagnostics=[],rows=kept)
        module.generate_abc_from_data=generate
        return module

    def test_good_export_is_returned_verbatim(self):
        module=self.fixture();original=module._fill_intervals
        result=('ABC',SimpleNamespace(diagnostics=[]))
        module.generate_abc_from_data=Mock(return_value=result)
        self.assertIs(generate_score(module,[]),result)
        module.generate_abc_from_data.assert_called_once_with([])
        self.assertIs(module._fill_intervals,original)

    def test_tail_and_internal_zero_cell_annotations_preserve_raw_rows(self):
        module=self.fixture();original=module._fill_intervals
        rows=[(0,.2,'C:maj'),(.2,.21,'F:maj'),(.21,.48,'G:maj'),(.48,.49,'C:maj')]
        before=list(rows)
        text,score=generate_score(module,rows)
        self.assertEqual(text,'validated ABC')
        self.assertEqual(score.rows,[rows[0],rows[2]])
        self.assertEqual(rows,before)
        self.assertEqual(len(score.diagnostics),2)
        self.assertIs(module._fill_intervals,original)

    def test_unrelated_errors_are_never_suppressed(self):
        module=self.fixture();original=module._fill_intervals
        module.generate_abc_from_data=Mock(side_effect=ValueError('Unsupported chord quality'))
        with self.assertRaisesRegex(ValueError,'Unsupported'):generate_score(module,[])
        self.assertEqual(module.generate_abc_from_data.call_count,1)
        self.assertIs(module._fill_intervals,original)

    def test_retry_failure_restores_original_exporter(self):
        module=self.fixture();original=module._fill_intervals
        module.generate_abc_from_data=Mock(side_effect=[ValueError('Interval is shorter than the ABC subbeat grid'),ValueError('overlapping quantized melody notes')])
        with self.assertRaisesRegex(ValueError,'overlapping'):generate_score(module,[])
        self.assertIs(module._fill_intervals,original)


if __name__=='__main__':unittest.main()
