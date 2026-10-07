"""Finite synthetic base proof. No public CLI/native-reader integration."""
import hashlib
import json
import os
import struct
import sys
import time
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from base_worker import CAPS, MIB, ROOT, run
sys.path.insert(0,str(ROOT/'review/task-002'))
from probe_pdf import case_baseline, case_shared_flood_2, case_damaged_page

WORD='http://schemas.openxmlformats.org/wordprocessingml/2006/main'

def zipped(path,xml):
    with ZipFile(path,'w',ZIP_DEFLATED) as archive:
        archive.writestr('word/document.xml',xml)


def main(root):
    root.mkdir(parents=True,exist_ok=False)
    report={'starting_head':os.popen('git rev-parse HEAD').read().strip(),
            'effective_limits':CAPS,'python':sys.version,'kernel':os.uname().release,
            'scope':'independent unwired base candidate; synthetic disposable inputs',
            'cases':{},'checks':{},'passed':False}
    started=time.monotonic()
    def record(name,path,kind,**kwargs):
        if time.monotonic()-started>110:
            raise RuntimeError('outer proof budget nearly exhausted')
        result=run(path,kind,**kwargs)
        report['cases'][name]={'input_bytes':path.stat().st_size,
            'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),**result}
        return result
    def check(name,value):
        report['checks'][name]=bool(value)
        if not value: raise RuntimeError(name)
    try:
        normal=root/'normal.docx'
        zipped(normal,f'<w:document xmlns:w="{WORD}"><w:body><w:p><w:r><w:t>Readable DOCX text</w:t></w:r></w:p></w:body></w:document>')
        result=record('normal_docx',normal,'docx')
        check('normal_docx_tokens',result['status']=='counted' and result['tokens']==4)
        pdf=root/'normal.pdf';case_baseline(pdf)
        result=record('normal_pdf',pdf,'pdf')
        check('normal_pdf_tokens',result['status']=='counted' and result['tokens']==3)
        bomb=root/'actual-expansion.docx'
        # XML whitespace expansion, not enormous extracted text; +1 byte proves
        # the cap from bytes actually delivered by the decompressor.
        zipped(bomb,f'<w:document xmlns:w="{WORD}"><w:body>'+(' '*(5*MIB))+'</w:body></w:document>')
        result=record('actual_expansion',bomb,'docx')
        check('actual_4mib_expansion',result['status']=='too_large' and result['actual_xml_bytes']==4*MIB+1)
        lying=root/'lying-metadata.docx'
        raw=bytearray(bomb.read_bytes());central=raw.index(b'PK\x01\x02');local=raw.index(b'PK\x03\x04')
        struct.pack_into('<I',raw,central+24,32);struct.pack_into('<I',raw,local+22,32)
        lying.write_bytes(raw)
        result=record('lying_metadata',lying,'docx')
        check('lying_metadata_rejected',result['status']=='failed' and result['tokens'] is None)
        deep=root/'depth.docx'
        zipped(deep,f'<w:document xmlns:w="{WORD}">'+('<w:r>'*130)+('</w:r>'*130)+'</w:document>')
        result=record('structural_depth',deep,'docx')
        check('depth_129_rejected',result['status']=='too_large' and result['xml_depth_peak']==129)
        elems=root/'elements.docx'
        zipped(elems,f'<w:document xmlns:w="{WORD}">'+('<w:r/>'*100001)+'</w:document>')
        result=record('structural_elements',elems,'docx')
        check('elements_100001_rejected',result['status']=='too_large' and result['xml_elements']==100001)
        aggregate=root/'aggregate.docx'
        with ZipFile(aggregate,'w',ZIP_DEFLATED) as archive:
            for name in ('word/document.xml','word/header1.xml','word/footer1.xml'):
                archive.writestr(name,f'<w:document xmlns:w="{WORD}">'+(' '*(3*MIB))+'</w:document>')
        result=record('aggregate_expansion',aggregate,'docx')
        check('aggregate_8mib_rejected',result['status']=='too_large' and result['actual_xml_bytes']==8*MIB+1)
        malformed=root/'malformed.docx';malformed.write_bytes(b'SYNTHETIC-NOT-ZIP')
        result=record('parser_failure',malformed,'docx')
        check('parser_failure_fixed_status',result['status']=='failed' and result['tokens'] is None)
        damaged=root/'damaged.pdf';case_damaged_page(damaged)
        result=record('damaged_pdf',damaged,'pdf')
        check('pdf_warnings_incomplete',result['status']=='partial' and result['tokens']>0 and result.get('pdf_warnings',0)>0)
        flood=root/'flood.pdf';case_shared_flood_2(flood)
        result=record('hostile_pdf',flood,'pdf')
        check('hostile_pdf_bounded',result['status'] in ('failed','timed_out','too_large') and result['seconds']<16)
        source=root/'text.txt';source.write_text('Readable ordinary text')
        result=record('oversized_ipc',source,'oversized')
        check('actual_12mib_ipc_rejection',result['status']=='too_large' and result['ipc_bytes_received']==12*MIB+1)
        result=record('timeout',source,'timeout',wall=.3)
        check('live_timeout',result['status']=='timed_out' and result['seconds']<1.5)
        result=record('crash',source,'crash')
        check('live_crash',result['status']=='failed')
        result=record('address_space',source,'memory')
        check('512mib_address_space_enforced',result['status']=='failed' and result.get('peak_rss_kib',512*1024)<512*1024)
        result=record('cpu',source,'cpu')
        check('10s_cpu_enforced',result['status']=='failed' and result['seconds']<15)
        # Escaping descendant's namespace inode and host PID/starttime are observed
        # externally before timeout; afterwards the same identities must be dead.
        import threading
        marker=root/'escaped-marker'
        source.write_text(str(marker))
        observed=[]
        def observe():
            end=time.monotonic()+1
            while time.monotonic()<end:
                if marker.exists():
                    inner=marker.read_text()
                    for entry in Path('/proc').iterdir():
                        if not entry.name.isdigit():continue
                        try:
                            status=(entry/'status').read_text()
                            nspid=next(line.split()[1:] for line in status.splitlines() if line.startswith('NSpid:'))
                            if len(nspid)>1 and nspid[-1]==inner:
                                stat=(entry/'stat').read_text().rsplit(')',1)[1].split()
                                observed.append({'host_pid':int(entry.name),'starttime':stat[19],
                                                 'session':stat[3],'nspid':nspid,'pid_namespace':os.readlink(entry/'ns/pid')})
                        except (OSError,StopIteration):pass
                    return
                time.sleep(.005)
        observer=threading.Thread(target=observe);observer.start()
        result=record('setsid_timeout',source,'escaped',wall=.8)
        observer.join()
        survivors=[]
        for identity in observed:
            try:
                stat=(Path('/proc')/str(identity['host_pid'])/'stat').read_text().rsplit(')',1)[1].split()
                if stat[19]==identity['starttime'] and stat[0]!='Z':survivors.append(identity['host_pid'])
            except OSError:pass
        report['setsid_observed']=observed
        report['setsid_survivors']=survivors
        check('setsid_descendant_killed',bool(observed) and not survivors and result['status']=='timed_out')
        # Same coordinator survives bad files and a later independent root. Each
        # file gets fresh CPU/AS limits, including after the ten-second CPU case.
        source.write_text('Readable ordinary text')
        result=record('continued_file',normal,'docx')
        check('cross_file_continuation',result['status']=='counted' and result['tokens']==4)
        other=root/'other-root';other.mkdir();plain=other/'text.txt';plain.write_text('Readable ordinary text')
        result=record('continued_root',plain,'text')
        check('cross_root_continuation',result['status']=='counted' and result['tokens']==3)
        report['passed']=True
    except Exception as exc:
        report['failure']=type(exc).__name__+': '+str(exc)
    finally:
        report['elapsed_seconds']=round(time.monotonic()-started,4)
        (root/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':report['passed'],'checks':report['checks'],'failure':report.get('failure'),'seconds':report['elapsed_seconds']}))
    return 0 if report['passed'] else 1

if __name__=='__main__':
    raise SystemExit(main(Path(sys.argv[1]).resolve()))
