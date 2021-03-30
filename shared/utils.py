import os
import sys
from os.path import isfile, abspath
from sys import exit, stderr
from subprocess import check_output, PIPE, Popen
import argparse
import shlex
from subprocess import PIPE

from os.path import isfile, isdir
# A->A
# C->C
# G->G
# T or U->T
# R->A or G
# Y->C or T
# S->G or C
# W->A or T
# K->G or T
# M->A or C
# B->C or G or T
# D->A or G or T
# H->A or C or T
# V->A or C or G
IUPAC_base_to_ACGT_base_dict = dict(zip(
    "ACGTURYSWKMBDHVN",
    ("A", "C", "G", "T", "T", "A", "C", "C", "A", "G", "A", "C", "A", "A", "A", "A")
))

IUPAC_base_to_num_dict = dict(zip(
    "ACGTURYSWKMBDHVN",
    (0, 1, 2, 3, 3, 0, 1, 1, 0, 2, 0, 1, 0, 0, 0, 0)
))
BASIC_BASES = set("ACGTU")

def is_file_exists(file_name, suffix=""):
    if not isinstance(file_name, str) or not isinstance(suffix, str):
        return False
    return isfile(file_name + suffix)

def is_folder_exists(folder_name, suffix=""):
    if not isinstance(folder_name, str) or not isinstance(suffix, str):
        return False
    return isdir(folder_name + suffix)


def file_path_from(file_name, suffix="", exit_on_not_found=False):
    if is_file_exists(file_name, suffix):
        return abspath(file_name)
    if exit_on_not_found:
        exit("[ERROR] file %s not found" % (file_name + suffix))
    return None

def folder_path_from(folder_name, create_not_found=True, exit_on_not_found=False):
    if is_folder_exists(folder_name):
        return abspath(folder_name)
    if exit_on_not_found:
        exit("[ERROR] folder %s not found" % (folder_name))
    if create_not_found:
        if not os.path.exists(folder_name):
            os.makedirs(abspath(folder_name))
            print("[INFO] Create folder %s" % (folder_name) , file=stderr)
            return abspath(folder_name)
    return None


def is_command_exists(command):
    if not isinstance(command, str):
        return False

    try:
        check_output("which %s" % (command), shell=True)
        return True
    except:
        return False


def executable_command_string_from(command_to_execute, exit_on_not_found=False):
    if is_command_exists(command_to_execute):
        return command_to_execute
    if exit_on_not_found:
        exit("[ERROR] %s executable not found" % (command_to_execute))
    return None


def subprocess_popen(args, stdin=None, stdout=PIPE, stderr=stderr, bufsize=8388608):
    return Popen(args, stdin=stdin, stdout=stdout, stderr=stderr, bufsize=bufsize, universal_newlines=True)


def str2bool(v):
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def region_from(ctg_name, ctg_start=None, ctg_end=None):
    """
    1-based region string [start, end]
    """
    if ctg_name is None:
        return ""
    if (ctg_start is None) != (ctg_end is None):
        return ""

    if ctg_start is None and ctg_end is None:
        return "{}".format(ctg_name)
    return "{}:{}-{}".format(ctg_name, ctg_start, ctg_end)

def reference_sequence_from(samtools_execute_command, fasta_file_path, regions):
    refernce_sequences = []
    region_value_for_faidx = " ".join(regions)

    samtools_faidx_process = subprocess_popen(
        shlex.split("{} faidx {} {}".format(samtools_execute_command, fasta_file_path, region_value_for_faidx))
    )
    while True:
        row = samtools_faidx_process.stdout.readline()
        is_finish_reading_output = row == '' and samtools_faidx_process.poll() is not None
        if is_finish_reading_output:
            break
        if row:
            refernce_sequences.append(row.rstrip())

    # first line is reference name ">xxxx", need to be ignored
    reference_sequence = "".join(refernce_sequences[1:])

    # uppercase for masked sequences
    reference_sequence = reference_sequence.upper()

    samtools_faidx_process.stdout.close()
    samtools_faidx_process.wait()
    if samtools_faidx_process.returncode != 0:
        return None

    return reference_sequence


def candidate_position_generator_from(
    candidate,
    flanking_base_num,
    begin_to_end
):
    for position in candidate:
        for i in range(position - (flanking_base_num + 1), position + (flanking_base_num + 1)):
            if i not in begin_to_end:
                begin_to_end[i] = [(position + (flanking_base_num + 1), position)]
            else:
                begin_to_end[i].append((position + (flanking_base_num + 1), position))
        yield position
    yield -1


def samtools_mpileup_generator_from(
    candidate,
    flanking_base_num,
    begin_to_end
):
    for position in candidate:
        for i in range(position - (flanking_base_num + 1), position + (flanking_base_num + 1)):
            if i not in begin_to_end:
                begin_to_end[i] = [(position + (flanking_base_num + 1), position)]
            else:
                begin_to_end[i].append((position + (flanking_base_num + 1), position))
        yield position
    yield -1

def samtools_view_process_from(
    ctg_name,
    ctg_start,
    ctg_end,
    samtools,
    bam_file_path
):
    have_start_and_end_position = ctg_start != None and ctg_end != None
    region_str = ("%s:%d-%d" % (ctg_name, ctg_start, ctg_end)) if have_start_and_end_position else ctg_name

    return subprocess_popen(
        shlex.split("%s view -F 2318 %s %s" % (samtools, bam_file_path, region_str))
    )

