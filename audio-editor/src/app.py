from flask import Flask, render_template, request, jsonify, send_file, url_for
import os
import subprocess
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import uuid
import tempfile
import shutil

app = Flask(__name__, template_folder='../templates', static_folder='../static')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(BASE_DIR, 'output')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

def detect_silences(input_file):
    cmd = [
        'ffmpeg', '-i', input_file, 
        '-af', 'silencedetect=n=-50dB:d=0.5', 
        '-f', 'null', '-'
    ]
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    silences = []
    lines = result.stdout.split('\n')
    
    for line in lines:
        if 'silence_start' in line:
            try:
                start = float(line.split('silence_start: ')[1].split()[0])
                silences.append({'start': start, 'end': None})
            except:
                continue
        elif 'silence_end' in line and silences:
            try:
                end = float(line.split('silence_end: ')[1].split('|')[0])
                if silences and silences[-1]['end'] is None:
                    silences[-1]['end'] = end
                    silences[-1]['duration'] = end - silences[-1]['start']
            except:
                continue
    
    return silences

def get_audio_info(input_file):
    cmd = [
        'ffprobe', '-v', 'quiet', '-print_format', 'json', 
        '-show_streams', '-show_format', input_file
    ]
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    info = json.loads(result.stdout)
    
    duration = float(info['format']['duration'])
    audio_stream = next(s for s in info['streams'] if s['codec_type'] == 'audio')
    
    return {
        'duration': duration,
        'sample_rate': int(audio_stream['sample_rate']),
        'channels': int(audio_stream['channels']),
        'bitrate': int(info['format']['bit_rate']) if 'bit_rate' in info['format'] else 0
    }

def get_file_duration(file_path):
    """Obtém duração real de um arquivo"""
    cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', file_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(result.stdout.strip())
    except:
        return 0

def process_audio_video_segments(input_file, output_file):
    """
    Corta ÁUDIO E VÍDEO juntos baseado nos silêncios detectados
    """
    silences = detect_silences(input_file)
    completed_silences = [s for s in silences if s.get('end')]
    
    if not completed_silences:
        cmd = [
            'ffmpeg', '-i', input_file,
            '-af', 'volume=1.2,afftdn',
            '-c:v', 'copy',
            '-y', output_file
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.returncode == 0
    
    audio_info = get_audio_info(input_file)
    total_duration = audio_info['duration']
    
    segments = []
    current_time = 0.0
    
    for silence in completed_silences:
        if silence['start'] > current_time + 0.1:
            segments.append({
                'start': current_time,
                'end': silence['start'],
                'duration': silence['start'] - current_time
            })
        current_time = silence['end']
    
    if current_time < total_duration - 0.1:
        segments.append({
            'start': current_time,
            'end': total_duration,
            'duration': total_duration - current_time
        })
    
    print(f"DEBUG: Video original: {total_duration:.2f}s")
    print(f"DEBUG: Silêncios removidos: {len(completed_silences)}")
    print(f"DEBUG: Segmentos finais: {len(segments)}")
    
    total_final_duration = sum(seg['duration'] for seg in segments)
    print(f"DEBUG: Duração final esperada: {total_final_duration:.2f}s")
    
    if not segments:
        return False
    
    temp_dir = tempfile.mkdtemp()
    temp_files = []
    
    try:
        for i, segment in enumerate(segments):
            temp_file = os.path.join(temp_dir, f"segment_{i:03d}.mp4")
            temp_files.append(temp_file)
            
            cmd = [
                'ffmpeg', '-i', input_file,
                '-ss', f"{segment['start']:.3f}",
                '-t', f"{segment['duration']:.3f}",
                '-c:v', 'libx264', '-crf', '23', '-preset', 'fast',
                '-c:a', 'aac', '-b:a', '128k',
                '-af', 'volume=1.2,afftdn',
                '-avoid_negative_ts', 'make_zero',
                '-y', temp_file
            ]
            
            print(f"DEBUG: Extraindo segmento {i+1}: {segment['start']:.2f}s - {segment['end']:.2f}s")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                print(f"ERRO no segmento {i}: {result.stderr}")
                return False
        
        if len(temp_files) == 1:
            shutil.copy2(temp_files[0], output_file)
        else:
            list_file = os.path.join(temp_dir, 'concat_list.txt')
            with open(list_file, 'w') as f:
                for temp_file in temp_files:
                    f.write(f"file '{temp_file}'\n")
            
            cmd = [
                'ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_file,
                '-c', 'copy',
                '-y', output_file
            ]
            
            print("DEBUG: Concatenando segmentos...")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                print(f"ERRO na concatenação: {result.stderr}")
                return False
        
        print(f"DEBUG: Arquivo final criado: {output_file}")
        
        if os.path.exists(output_file):
            final_duration = get_file_duration(output_file)
            print(f"DEBUG: Duração final real: {final_duration:.2f}s")
            print(f"DEBUG: Redução: {total_duration - final_duration:.2f}s")
        
        return True
        
    except Exception as e:
        print(f"ERRO durante processamento: {e}")
        return False
    
    finally:
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

def process_audio(input_file, output_file):
    """
    Versão final que realmente funciona
    """
    is_video = input_file.lower().endswith(('.mp4', '.avi', '.mkv', '.mov', '.wmv'))
    
    if is_video:
        return process_audio_video_segments(input_file, output_file)
    else:
        cmd = [
            'ffmpeg', '-i', input_file,
            '-af', 
            'silenceremove=start_periods=1:start_duration=0:start_threshold=-50dB,'
            'silenceremove=stop_periods=-1:stop_duration=0.5:stop_threshold=-50dB,'
            'volume=1.2,afftdn',
            '-y', output_file
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            print(f"ERRO FFmpeg: {result.stderr}")
        
        return result.returncode == 0

def generate_report(silences, audio_info, output_file):
    plt.figure(figsize=(12, 8))
    
    plt.subplot(2, 2, 1)
    if silences:
        silence_starts = [s['start'] for s in silences if s.get('end')]
        silence_durations = [s['duration'] for s in silences if s.get('end')]
        
        plt.scatter(silence_starts, silence_durations, alpha=0.7)
        plt.xlabel('Tempo (s)')
        plt.ylabel('Duração do Silêncio (s)')
        plt.title('Distribuição de Silêncios')
        plt.grid(True, alpha=0.3)
    else:
        plt.text(0.5, 0.5, 'Nenhum silêncio detectado', ha='center', va='center', transform=plt.gca().transAxes)
        plt.title('Distribuição de Silêncios')
    
    plt.subplot(2, 2, 2)
    total_silence = sum(s['duration'] for s in silences if s.get('end'))
    audio_time = audio_info['duration'] - total_silence
    
    plt.pie([audio_time, total_silence], labels=['Áudio', 'Silêncio'], 
            autopct='%1.1f%%', startangle=90, colors=['#4CAF50', '#FF5722'])
    plt.title('Proporção Áudio vs Silêncio')
    
    plt.subplot(2, 2, 3)
    if silences:
        plt.hist([s['duration'] for s in silences if s.get('end')], bins=10, alpha=0.7, color='#FF9800')
        plt.xlabel('Duração (s)')
        plt.ylabel('Frequência')
        plt.title('Histograma de Durações de Silêncio')
        plt.grid(True, alpha=0.3)
    else:
        plt.text(0.5, 0.5, 'Nenhum silêncio detectado', ha='center', va='center', transform=plt.gca().transAxes)
        plt.title('Histograma de Durações de Silêncio')
    
    plt.subplot(2, 2, 4)
    info_text = f"""Informações do Arquivo:
Duração: {audio_info['duration']:.2f}s
Taxa de Amostragem: {audio_info['sample_rate']}Hz
Canais: {audio_info['channels']}
Bitrate: {audio_info['bitrate']}bps

Silêncios Detectados: {len([s for s in silences if s.get('end')])}
Tempo Total de Silêncio: {total_silence:.2f}s
Tempo Economizado: {total_silence:.2f}s"""
    
    plt.text(0.1, 0.9, info_text, transform=plt.gca().transAxes, fontsize=9,
             verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    plt.axis('off')
    plt.title('Estatísticas')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nenhum arquivo selecionado'})
    
    if file:
        file_id = str(uuid.uuid4())
        filename = f"{file_id}_{file.filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        print(f"DEBUG: Arquivo salvo em: {file_path}")
        
        try:
            audio_info = get_audio_info(file_path)
            silences = detect_silences(file_path)
            
            output_filename = f"processed_{filename}"
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
            
            print(f"DEBUG: Arquivo de saída será salvo em: {output_path}")
            
            if process_audio(file_path, output_path):
                print(f"DEBUG: Processamento concluído. Verificando se arquivo existe: {os.path.exists(output_path)}")
                
                final_duration = get_file_duration(output_path)
                real_time_saved = audio_info['duration'] - final_duration
                
                print(f"DEBUG: Duração original: {audio_info['duration']:.2f}s")
                print(f"DEBUG: Duração final: {final_duration:.2f}s")
                print(f"DEBUG: Tempo realmente economizado: {real_time_saved:.2f}s")
                
                report_filename = f"report_{file_id}.png"
                report_path = os.path.join(app.config['OUTPUT_FOLDER'], report_filename)
                generate_report(silences, audio_info, report_path)
                
                return jsonify({
                    'success': True,
                    'file_id': file_id,
                    'original_duration': audio_info['duration'],
                    'final_duration': final_duration,
                    'real_time_saved': real_time_saved,
                    'silences_count': len([s for s in silences if s.get('end')]),
                    'total_silence_time': sum(s['duration'] for s in silences if s.get('end')),
                    'output_file': output_filename,
                    'report_file': report_filename
                })
            else:
                return jsonify({'error': 'Erro no processamento do arquivo'})
                
        except Exception as e:
            print(f"DEBUG: Erro durante processamento: {str(e)}")
            return jsonify({'error': f'Erro: {str(e)}'})

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    print(f"DEBUG: Tentando baixar arquivo: {file_path}")
    print(f"DEBUG: Arquivo existe? {os.path.exists(file_path)}")
    
    if not os.path.exists(file_path):
        return jsonify({'error': f'Arquivo não encontrado: {file_path}'}), 404
    
    return send_file(file_path, as_attachment=True)

@app.route('/report/<filename>')
def view_report(filename):
    file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    
    if not os.path.exists(file_path):
        return jsonify({'error': f'Relatório não encontrado: {file_path}'}), 404
    
    return send_file(file_path)

@app.route('/debug/files')
def debug_files():
    upload_files = os.listdir(app.config['UPLOAD_FOLDER']) if os.path.exists(app.config['UPLOAD_FOLDER']) else []
    output_files = os.listdir(app.config['OUTPUT_FOLDER']) if os.path.exists(app.config['OUTPUT_FOLDER']) else []
    
    return jsonify({
        'base_dir': BASE_DIR,
        'upload_folder': app.config['UPLOAD_FOLDER'],
        'output_folder': app.config['OUTPUT_FOLDER'],
        'upload_files': upload_files,
        'output_files': output_files
    })

if __name__ == '__main__':
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"UPLOAD_FOLDER: {app.config['UPLOAD_FOLDER']}")
    print(f"OUTPUT_FOLDER: {app.config['OUTPUT_FOLDER']}")
    
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    
    print(f"Pastas criadas:")
    print(f"- Upload: {os.path.exists(app.config['UPLOAD_FOLDER'])}")
    print(f"- Output: {os.path.exists(app.config['OUTPUT_FOLDER'])}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
