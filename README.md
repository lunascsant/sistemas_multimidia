# Editor Automático de Áudio

Sistema web para detecção e remoção automática de silêncios em arquivos de áudio e vídeo.

## Pré-requisitos

- Python 3.8+
- FFmpeg instalado no sistema

### Instalar FFmpeg

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Baixar do [site oficial do FFmpeg](https://ffmpeg.org/download.html)

## Instalação

1. Clone ou baixe o projeto

2. Certifique-se de ter todos os arquivos necessários

3. Instale as dependências:
```bash
cd audio-editor
pip install -r requirements.txt
```

## Uso

1. Inicie a aplicação:
```bash
python src/app.py
```

2. Abra no navegador: `http://localhost:5000`

3. Faça upload de um arquivo (MP3, WAV, MP4, AVI, MKV)

4. Aguarde o processamento e baixe o resultado

## Funcionalidades

- **Detecção automática de silêncios** (>= 0.5s, < -50dB)
- **Remoção de pausas desnecessárias**
- **Normalização de volume** (+20%)
- **Redução de ruído** (filtro FFT)
- **Relatórios visuais** com estatísticas
- **Sincronização áudio/vídeo** para arquivos de vídeo

## Formatos Suportados

- **Áudio:** MP3, WAV, FLAC, AAC
- **Vídeo:** MP4, AVI, MKV, MOV, WMV

## Estrutura do Projeto

```
audio-editor/
├── src/app.py              # Aplicação principal
├── templates/index.html    # Interface web
├── static/
│   ├── css/style.css      # Estilos
│   └── js/script.js       # JavaScript
├── uploads/               # Arquivos de entrada
└── output/                # Arquivos processados
```

## Exemplo de Uso

- **Entrada:** Vídeo de 5 minutos com pausas longas
- **Saída:** Vídeo de 3 minutos com silêncios removidos
- **Resultado:** Áudio e vídeo perfeitamente sincronizados

## Requisitos Atendidos

✅ Aplicação baseada na Web  
✅ Codificação/Transcodificação de áudio e vídeo  
✅ Processamento de áudio com técnicas de IA  

---

**Universidade Federal de Juiz de Fora - UFJF**  
Sistemas Multimídia - Prof. Marcelo Moreno
