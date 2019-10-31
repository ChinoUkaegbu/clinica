# coding: utf8


def zip_nii(in_file, same_dir=False):
    from os import getcwd
    from os.path import abspath, join
    import gzip
    import shutil
    from nipype.utils.filemanip import split_filename
    from traits.trait_base import _Undefined

    if (in_file is None) or isinstance(in_file, _Undefined):
        return None

    if not isinstance(in_file, str):  # type(in_file) is list:
        return [zip_nii(f, same_dir) for f in in_file]

    orig_dir, base, ext = split_filename(str(in_file))

    # Already compressed
    if ext[-3:].lower() == ".gz":
        return in_file
    # Not compressed

    if same_dir:
        out_file = abspath(join(orig_dir, base + ext + '.gz'))
    else:
        out_file = abspath(join(getcwd(), base + ext + '.gz'))

    with open(in_file, 'rb') as f_in, gzip.open(out_file, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

    return out_file


def unzip_nii(in_file):
    from nipype.utils.filemanip import split_filename
    from nipype.algorithms.misc import Gunzip
    from traits.trait_base import _Undefined

    if (in_file is None) or isinstance(in_file, _Undefined):
        return None

    if not isinstance(in_file, str):  # type(in_file) is list:
        return [unzip_nii(f) for f in in_file]

    _, base, ext = split_filename(in_file)

    # Not compressed
    if ext[-3:].lower() != ".gz":
        return in_file
    # Compressed
    gunzip = Gunzip(in_file=in_file)
    gunzip.run()
    return gunzip.aggregate_outputs().out_file


def save_participants_sessions(participant_ids, session_ids, out_folder, out_file=None):
    """
    Save <participant_ids> <session_ids> in <out_folder>/<out_file> TSV file.
    """
    import os
    import errno
    import pandas
    from clinica.utils.stream import cprint

    assert(len(participant_ids) == len(session_ids))

    try:
        os.makedirs(out_folder)
    except OSError as e:
        if e.errno != errno.EEXIST:  # EEXIST: folder already exists
            raise e

    if out_file:
        tsv_file = os.path.join(out_folder, out_file)
    else:
        tsv_file = os.path.join(out_folder, 'participants.tsv')

    try:
        data = pandas.DataFrame({
            'participant_id': participant_ids,
            'session_id': session_ids,
        })
        data.to_csv(tsv_file, sep='\t', index=False, encoding='utf-8')
    except Exception as e:
        cprint("Impossible to save %s with pandas" % out_file)
        raise e


def get_subject_id(bids_or_caps_file):
    """
    Extracts "sub-<participant_id>_ses-<session_label>" from BIDS or CAPS file
    """
    import re

    m = re.search(r'(sub-[a-zA-Z0-9]+)/(ses-[a-zA-Z0-9]+)', bids_or_caps_file)

    if m is None:
        raise ValueError(
            'Input filename is not in a BIDS or CAPS compliant format.'
            ' It does not contain the subject and session information.')

    subject_id = m.group(1) + '_' + m.group(2)

    return subject_id


def extract_image_ids(bids_or_caps_files):
    """Extract image IDs (e.g. ['sub-CLNC01_ses-M00', 'sub-CLNC01_ses-M18']  from `bids_or_caps_files`."""
    import re
    id_bids_or_caps_files = [re.search(r'(sub-[a-zA-Z0-9]+)_(ses-[a-zA-Z0-9]+)', file).group()
                             for file in bids_or_caps_files]
    return id_bids_or_caps_files


def extract_subjects_sessions_from_filename(bids_or_caps_files):
    """Extract subjects/sessions (e.g. ['sub-CLNC01', 'sub-CLNC01']/['ses-M00', 'ses-M18'] from `bids_or_caps_files`."""
    id_bids_or_caps_files = extract_image_ids(bids_or_caps_files)
    split = [image_id.split('_')
             for image_id in id_bids_or_caps_files]
    subject_ids = [p_id[0] for p_id in split]
    session_ids = [s_id[1] for s_id in split]
    return subject_ids, session_ids


def extract_crash_files_from_log_file(filename):
    """Extract crash files (*.pklz) from `filename`.
    """
    import os
    import re

    assert(os.path.isfile(filename)),\
        'extract_crash_files_from_log_file: filename parameter is not a file (%s)' % filename

    log_file = open(filename, "r")
    crash_files = []
    for line in log_file:
        if re.match("(.*)crashfile:(.*)", line):
            crash_files.append(line.replace('\t crashfile:', '').replace('\n', ''))

    return crash_files


def read_participant_tsv(tsv_file):
    """Extract participant IDs and session IDs from TSV file.

    Raise:
        ClinicaException if tsv_file is not a file
        ClinicaException if participant_id or session_id column is missing from TSV file
    """
    import os
    import pandas as pd
    from colorama import Fore
    from clinica.utils.exceptions import ClinicaException

    if not os.path.isfile(tsv_file):
        raise ClinicaException(
            "\n%s[Error] The TSV file you gave is not a file.%s\n"
            "\n%sError explanations:%s\n"
            " - Clinica expected the following path to be a file: %s%s%s\n"
            " - If you gave relative path, did you run Clinica on the good folder?" %
            (Fore.RED, Fore.RESET,
             Fore.YELLOW, Fore.RESET,
             Fore.BLUE, tsv_file, Fore.RESET)
        )
    ss_df = pd.io.parsers.read_csv(tsv_file, sep='\t')
    if 'participant_id' not in list(ss_df.columns.values):
        raise ClinicaException(
            "\n%s[Error] The TSV file does not contain participant_id column (path: %s)%s" %
            (Fore.RED, tsv_file, Fore.RESET)
        )
    if 'session_id' not in list(ss_df.columns.values):
        raise ClinicaException(
            "\n%s[Error] The TSV file does not contain session_id column (path: %s)%s" %
            (Fore.RED, tsv_file, Fore.RESET)
        )
    participants = list(ss_df.participant_id)
    sessions = list(ss_df.session_id)

    # Remove potential whitespace in participant_id or session_id
    return [sub.strip(' ') for sub in participants], [ses.strip(' ') for ses in sessions]


def get_subject_session_list(input_dir, ss_file=None, is_bids_dir=True, use_session_tsv=False, tsv_dir=None):
    """Parses a BIDS or CAPS directory to get the subjects and sessions.

    This function lists all the subjects and sessions based on the content of
    the BIDS or CAPS directory or (if specified) on the provided
    subject-sessions TSV file.

    Args:
        input_dir: A BIDS or CAPS directory path.
        ss_file: A subjects-sessions file (.tsv format).
        is_bids_dir: Indicates if input_dir is a BIDS or CAPS directory
        use_session_tsv (boolean): Specify if the list uses the sessions listed in the sessions.tsv files
        tsv_dir (str): if TSV file does not exist, it will be created in output_dir. If
            not specified, output_dir will be in <tmp> folder

    Returns:
        subjects: A subjects list.
        sessions: A sessions list.
    """
    import os
    import tempfile
    from time import time, strftime, localtime
    import clinica.iotools.utils.data_handling as cdh

    if not ss_file:
        if tsv_dir:
            output_dir = tsv_dir
        else:
            output_dir = tempfile.mkdtemp()
        timestamp = strftime('%Y%m%d_%H%M%S', localtime(time()))
        tsv_file = 'subjects_sessions_list_%s.tsv' % timestamp
        ss_file = os.path.join(output_dir, tsv_file)

        cdh.create_subs_sess_list(
            input_dir=input_dir,
            output_dir=output_dir,
            file_name=tsv_file,
            is_bids_dir=is_bids_dir,
            use_session_tsv=use_session_tsv)

    participant_ids, session_ids = read_participant_tsv(ss_file)
    return session_ids, participant_ids


def get_unique_subjects(in_subject_list, in_session_list):
    """Get unique participant IDs

    The function to read the .tsv file returns the following
    participant_id and session_id lists:
    participant1, participant1, ..., participant2, participant2, ...
    session1    , session2    , ..., session1    , session2    , ...
    This function returns a list where all participants are only selected
    once:
    participant1, participant2, ..., participant_n
    and for each participant, the list of corresponding session id
    eg.:
    participant1 -> [session1, session2]
    participant2 -> [session1]
    ...
    participant_n -> [session1, session2, session3]

    Args:
        in_subject_list (list of strings): list of participant_id
        in_session_list (list of strings): list of session_id

    Returns:
        out_unique_subject_list (list of strings): list of
            participant_id, where each participant appears only once
        out_persubject_session_list2 (list of list): list of list
            (list2) of session_id associated to any single participant
    """

    import numpy as np

    subject_array = np.array(in_subject_list)
    session_array = np.array(in_session_list)

    # The second returned element indicates for each participant_id the
    # element they correspond to in the 'unique' list. We will use this
    # to link each session_id in the repeated list of session_id to
    # their corresponding unique participant_id

    unique_subject_array, out_inverse_positions = np.unique(
        subject_array, return_inverse=True)
    out_unique_subject_list = unique_subject_array.tolist()

    subject_number = len(out_unique_subject_list)
    out_persubject_session_list2 = [
        session_array[
            out_inverse_positions == subject_index
            ].tolist() for subject_index in range(subject_number)]

    return out_unique_subject_list, out_persubject_session_list2
