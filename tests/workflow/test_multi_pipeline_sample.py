""" Tests for case in which multiple pipelines process a single sample. """

import os
import time
import pytest
from pypiper import Stage
from pypiper.utils import checkpoint_filepath
from tests.helpers import fetch_checkpoint_files, named_param, SafeTestPipeline


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


READ_ALIGNER_FILENAME = "aligner.lst"
PEAK_CALLER_FILENAME = "caller.lst"


# Dummy functions used as elements of pipeline stages() collections.
def merge_input():
    pass

def qc():
    pass

def align_reads():
    pass

def call_peaks():
    pass



class FunctionNameWriterPipeline(SafeTestPipeline):
    
    
    def __init__(self, name, outfolder, filename, functions):
        """
        Name and outfolder go to generic pipeline ctor; filename and functions
        collection are used specifically by instances of this class.

        :param str name: Name for this pipeline.
        :param str outfolder: Path to pipeline's output folder.
        :param str filename: Name for file in which to write function names.
        :param Sequence[callable] functions: Functions on which this pipeline
            is to operate (i.e., the functions for which name should be
            written to output file).
        """
        self.name_output_file = filename
        self.functions = functions
        super(FunctionNameWriterPipeline, self).__init__(
                name=name, outfolder=outfolder)


    def write_name(self, func):
        """
        Write the name of a function to this pipeline's output file.

        :param callable func: Name of function to write to the output file.
        """
        outpath = os.path.join(self.outfolder, self.name_output_file)
        with open(outpath, 'a') as f:
            f.write(func.__name__ + os.linesep)


    def stages(self):
        return [Stage(self.write_name, (f, ), name=f.__name__)
                for f in self.functions]



@pytest.fixture
def read_aligner(tmpdir):
    """ Provide test case with a read aligner pipeline instance. """
    return FunctionNameWriterPipeline(
            "read-aligner", tmpdir.strpath,
            READ_ALIGNER_FILENAME, [merge_input, qc, align_reads])



@pytest.fixture
def peak_caller(tmpdir):
    """ Provide test case with a 'PeakCaller' pipeline instance. """
    return FunctionNameWriterPipeline(
            "peak-caller", tmpdir.strpath,
            PEAK_CALLER_FILENAME, [align_reads, call_peaks])



@named_param("test_type", ["checkpoint", "effect"])
def test_pipeline_checkpoint_respect_sensitivity_checkpoint_perspective(
        read_aligner, peak_caller, test_type):
    """ Pipeline can skip past its stage(s) for which checkpoint exists. """

    # Negative control to start test, that we have no checkpoint files.
    assert [] == fetch_checkpoint_files(read_aligner.manager)

    # Generate some checkpoints.
    read_aligner.run()

    # Verify that we created each of the checkpoints.
    expected = [checkpoint_filepath(f.__name__, read_aligner.manager)
                for f in read_aligner.functions]
    observed = fetch_checkpoint_files(read_aligner.manager)
    assert set(expected) == set(observed)

    # Collect checkpoint file timestamps for comparison after second run.
    timestamps = {f: os.path.getmtime(f) for f in observed}

    # Remove the checkpoint for the final stage.
    last_aligner_stage = read_aligner.functions[-1]
    last_aligner_checkfile = checkpoint_filepath(
            last_aligner_stage, read_aligner.manager)
    os.remove(last_aligner_checkfile)

    # Verify removal of final stage checkpoint file.
    assert all([os.path.isfile(f) for f in expected[:-1]])
    assert not os.path.exists(last_aligner_checkfile)
    assert set(expected) != set(fetch_checkpoint_files(read_aligner.manager))

    # Delay briefly so that we can more reliably compare checkpoint file
    # timestamps after a second pipeline run.
    time.sleep(0.1)

    # Repeat the pipeline's execution, but now with checkpoint file(s) for a
    # subset of its stages in place.
    read_aligner.run()

    # Verify that we've restored the full collection of the pipeline's
    # checkpoint files to existence.
    observed = fetch_checkpoint_files(read_aligner.manager)
    exp = set(expected)
    obs = set(observed)
    assert set(expected) == set(observed), \
            "Expected only:\n{}\nExpected and observed:\n{}\nObserved only:\n{}".format(
                    exp - obs, exp & obs, obs - exp)

    # Verify the we didn't recreate the checkpoint file for each skipped stage.
    for f in expected[:-1]:
        expected_timestamp = timestamps[f]
        observed_timestamp = os.path.getmtime(f)
        assert expected_timestamp == observed_timestamp

    # Verify the we did in fact recreate the checkpoint file for the stage
    # that was rerun.
    assert os.path.getmtime(last_aligner_checkfile) > \
           timestamps[last_aligner_checkfile], \
            "Recreated checkpoint file ('{}') should be newer than original".\
           format(last_aligner_checkfile)



def test_pipeline_checkpoint_sensitivity_effect_perspective():
    pass



@pytest.mark.skip("not implemented")
def test_pipeline_can_overwrite_checkpoints():
    pass



@pytest.mark.skip("not implemented")
def test_different_pipeline_checkpoints_are_unique_for_the_sample(tmpdir):
    pass



@pytest.mark.skip("not implemented")
def test_pipeline_checkpoint_respect_specificity():
    pass
