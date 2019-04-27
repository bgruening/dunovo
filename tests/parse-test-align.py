#!/usr/bin/env python3
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
import sys
import errno
import random
import logging
import argparse
assert sys.version_info.major >= 3, 'Python 3 required'

REVCOMP_TABLE = str.maketrans('acgtrymkbdhvACGTRYMKBDHV', 'tgcayrkmvhdbTGCAYRKMVHDB')

DESCRIPTION = """Generate test files from a human-readable alignment."""


def make_argparser():
  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.add_argument('alignment', type=argparse.FileType('r'), nargs='?', default=sys.stdin,
    help='The input alignment file. Omit to read from stdin.')
  parser.add_argument('-1', '--fq1', type=argparse.FileType('w'),
    help='Write the first-mate reads to this fastq file. Warning: will overwrite any existing file.')
  parser.add_argument('-2', '--fq2', type=argparse.FileType('w'),
    help='Write the first-mate reads to this fastq file. Warning: will overwrite any existing file.')
  parser.add_argument('-r', '--ref', type=argparse.FileType('w'),
    help='Write the reference sequence to this file. Warning: will overwrite any existing file.')
  parser.add_argument('-c', '--const', default='TACGT',
    help='Default: %(default)s')
  parser.add_argument('-q', '--default-qual', type=int, default=40,
    help='Default: %(default)s')
  parser.add_argument('-l', '--log', type=argparse.FileType('w'), default=sys.stderr,
    help='Print log messages to this file instead of to stderr. Warning: Will overwrite the file.')
  parser.add_argument('-Q', '--quiet', dest='volume', action='store_const', const=logging.CRITICAL,
    default=logging.WARNING)
  parser.add_argument('-v', '--verbose', dest='volume', action='store_const', const=logging.INFO)
  parser.add_argument('-D', '--debug', dest='volume', action='store_const', const=logging.DEBUG)
  return parser


def main(argv):

  parser = make_argparser()
  args = parser.parse_args(argv[1:])

  logging.basicConfig(stream=args.log, level=args.volume, format='%(message)s')
  tone_down_logger()

  qual_char = chr(args.default_qual+32)

  if args.fq1 and args.fq2:
    fq_files = [args.fq1, args.fq2]
  else:
    fq_files = []

  barlen = None

  ref_seq = None
  family_num = 0
  pair_num = 0
  first_mate = None
  last_barcode = None
  for line_raw in args.alignment:
    if line_raw.startswith('#'):
      continue
    prefix = line_raw.split()[0]
    line = line_raw[len(prefix):].rstrip()
    if not line:
      continue
    if prefix.startswith('f'):
      raw_ref_seq = line.lstrip()
      if args.ref:
        ref_seq = raw_ref_seq.replace('-', '')
        args.ref.write('>ref\n')
        args.ref.write(ref_seq+'\n')
    elif prefix.startswith('r'):
      assert raw_ref_seq is not None, line_raw
      mate = int(prefix[1])
      if first_mate is None:
        first_mate = mate
      barcode = prefix[2:]
      if barcode != last_barcode:
        family_num += 1
        pair_num = 0
        if barlen is not None and barlen != len(barcode):
          fail('Error: Variable barcode lengths encountered. Barcode {!r} length != {}.'
               .format(barcode, barlen))
        barlen = len(barcode)
      if mate == first_mate:
        pair_num += 1
      raw_seq, pos, direction = get_raw_seq(line)
      tags = (barcode[:barlen//2], barcode[barlen//2:])
      final_seq = substitute_ref_bases(raw_seq, pos, raw_ref_seq)
      if fq_files:
        for line in format_read(final_seq, direction, mate, family_num, pair_num, tags, args.const,
                                qual_char):
          fq_files[mate-1].write(line+'\n')
      last_barcode = barcode

  print(barlen)


def get_raw_seq(line):
  direction = None
  seq = line.lstrip(' ')
  if seq.endswith('+'):
    direction = 'forward'
    seq = seq[:-1]
    pos = len(line) - len(seq)
  elif seq.startswith('-'):
    direction = 'reverse'
    seq = seq[1:]
    pos = len(line) - len(seq) + 1
  else:
    fail('A +/- direction is required at the 3\' end of the read.')
  return seq, pos, direction


def substitute_ref_bases(raw_seq, pos, ref_seq):
  """Replace dots in the raw sequence with reference bases."""
  final_seq = ''
  for i, raw_char in enumerate(raw_seq):
    if raw_char == '.':
      ref_char = ref_seq[pos+i-1]
      if ref_char != '-':
        final_seq += ref_char
    elif raw_char != '-':
      final_seq += raw_char
  return final_seq


def format_read(seq, direction, mate, family_num, pair_num, tags, const, qual_char):
  # Read name (line 1):
  if (direction == 'forward' and mate == 1) or (direction == 'reverse' and mate == 2):
    order = 'ab'
  else:
    order = 'ba'
  yield '@fam{}.{}.pair{} mate{}'.format(family_num, order, pair_num, mate)
  # Read sequence (line 2):
  if order == 'ab':
    tags_ordered = tags
  if order == 'ba':
    tags_ordered = list(reversed(tags))
  tag = tags_ordered[mate-1]
  if direction == 'reverse':
    yield tag + const + revcomp(seq)
  else:
    yield tag + const + seq
  # Plus (line 3):
  yield '+'
  # Quality scores (line 4):
  read_len = len(tag + const + seq)
  yield qual_char * read_len


def revcomp(seq):
  return seq.translate(REVCOMP_TABLE)[::-1]


def rand_seq(length):
  barcode = ''
  for i in range(length):
    barcode += random.choice('ACGT')
  return barcode


def tone_down_logger():
  """Change the logging level names from all-caps to capitalized lowercase.
  E.g. "WARNING" -> "Warning" (turn down the volume a bit in your log files)"""
  for level in (logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG):
    level_name = logging.getLevelName(level)
    logging.addLevelName(level, level_name.capitalize())


def fail(message):
  logging.critical(message)
  if __name__ == '__main__':
    sys.exit(1)
  else:
    raise Exception('Unrecoverable error')


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except IOError as ioe:
    if ioe.errno != errno.EPIPE:
      raise
