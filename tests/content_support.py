"""Read the actual YAML, not a second copy of lesson code."""
from pathlib import Path
from markdown_it import MarkdownIt
from tools.validate import load_model
ROOT=Path(__file__).resolve().parents[1]
MODEL=load_model(ROOT/'content',ROOT/'content/course.yaml')
MD=MarkdownIt('commonmark',{'html':False})

def fields(lesson):
    for step in lesson['steps']:
        for key,value in step.items():
            if key.endswith('Md'):
                yield f"{step['id']}/{key}",value
        for opt in step.get('options',[]):
            for key,value in opt.items():
                if key.endswith('Md'):
                    yield f"{step['id']}/options/{opt['id']}/{key}",value

def blocks(lid):
    result={}
    for field,text in fields(MODEL['lessons'][lid]):
        for i,token in enumerate(t for t in MD.parse(text) if t.type=='fence' and t.info.strip()=='python'):
            result[f'{field}/{i}']=token.content
    return result

def part(lid, step, field='bodyMd', index=0):
    return blocks(lid)[f'{step}/{field}/{index}']

def solution(lid):
    return '\n'.join(code for key,code in blocks(lid).items() if key.startswith('s-practice/solutionMd/'))
