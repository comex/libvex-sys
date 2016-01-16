# This script is released to the public domain.

import subprocess, re, os
pub = 'libvex-tob/VEX/pub'

# add #define constants as enums
enum_constants = 'enum XxxConstants {\n'
hfiles = ''.join(open(os.path.join(pub, x)).read() for x in ['libvex.h', 'libvex_s390x_common.h'])
for name in re.findall('^#define +([A-Z0-9_]+) +', hfiles, flags=re.M):
    enum_constants += 'XxxTheConstant%s = %s,\n' % (name, name)
enum_constants += '};\n'

inc_h = '''
#include <libvex.h>
#include <libvex_guest_x86.h>
#include <libvex_guest_amd64.h>
#include <libvex_guest_arm.h>
#include <libvex_guest_arm64.h>
#include <libvex_guest_mips32.h>
#include <libvex_guest_mips64.h>
#include <libvex_guest_ppc32.h>
#include <libvex_guest_ppc64.h>
#include <libvex_guest_s390x.h>
#include <libvex_s390x_common.h>
''' + enum_constants
open('inc.h', 'w').write(inc_h)

output = subprocess.check_output(['bindgen', '-I'+pub, 'inc.h'])
# Remove V128 and V256, which are useless and messy
output = re.sub('#\[repr\(C\)\].*?pub type V(128|256) = [^\n]*', '', output, flags=re.S)
# Name types which have exactly one alias
aliases = {}
for source, dest in re.findall('pub type ([^ ]*) = ((?:Enum|Struct)_[^ ]+);', output):
    aliases.setdefault(dest, []).append(source)
for dest, sources in aliases.iteritems():
    if len(sources) == 1:
        source = sources[0]
        output = re.sub(r'\b' + re.escape(dest) + r'\b', source, output)
        output = output.replace('\npub type %s = %s;' % (source, source), '')

# Remove VexGuestX86SegDescr
output = re.sub('pub struct VexGuestX86SegDescr.*(?=pub struct VexGuestAMD64State)', '', output, flags=re.S)

# Identify Ico, Iex, Ist, fxState, alwaysDefd
for field_name, out_name in [
    ('Ico', 'Ico'), ('Iex', 'Iex'), ('Ist', 'Ist'),
    ('fxState', 'FxState'), ('alwaysDefd', 'AlwaysDefd')
]:
    union_name = re.search('pub '+field_name+': \[?((?:Union|Struct)_Unnamed.*?)[,;]', output).group(1)
    output = output.replace(union_name, out_name)

# Identify Iex and Ist case structs
impl_pos = [(m.start(), m.group(1)) for m in re.finditer('^impl ([^ ]*) {', output, flags=re.M)]
replacements = []
for m in re.finditer('pub unsafe fn ([^ ]*)\(\&mut self\) -> \*mut (Struct_Unnamed[0-9]+) {', output):
    field_name, struct_name = m.groups()
    ty_name = None
    for start, name in impl_pos:
        if start < m.start():
            ty_name = name
    replacements.append((struct_name, ty_name + '_S_' + field_name))
for source, dest in replacements:
    output = output.replace(source, dest)

# fix some outright brokenness; todo bug report
output = output.replace('pub _bindgen_bitfield_1_: IREffect,', 'pub fx: u16,')
output = output.replace('pub status: Enum_Unnamed65,', 'pub status: u32,')
output = '''
#![allow(non_snake_case, non_upper_case_globals, non_camel_case_types)]
extern crate libc;
''' + output

# all done?
assert 'Unnamed' not in output

output = output.replace('XxxTheConstant', '')

output = re.sub('pub struct ([^ ]*) {\n}', 'pub struct \\1;', output)

output = re.sub('(?<=::libc::c_uint = )-([0-9]+)', lambda m: str(2**32 - int(m.group(1))), output)

# Make handy submodules
for prefix in ('Iop', 'Iex', 'Ico'):
    names = set(re.findall('const (%s_[a-zA-Z0-9_]+)' % (prefix,), output))
    output += 'pub mod %sConsts {\n' % (prefix,)
    for name in names:
        output += '    pub use ::%s;\n' % (name,)
    output += '}\n'

open('src/lib.rs', 'w').write(output)

os.unlink('inc.h')
