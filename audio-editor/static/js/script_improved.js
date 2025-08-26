document.addEventListener('DOMContentLoaded', function() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const progressSection = document.getElementById('progressSection');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const resultsSection = document.getElementById('resultsSection');

    uploadArea.addEventListener('click', () => fileInput.click());
    
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });
    
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    function handleFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        uploadArea.style.display = 'none';
        progressSection.style.display = 'block';
        resultsSection.style.display = 'none';
        
        simulateProgress();
        
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            progressSection.style.display = 'none';
            
            if (data.success) {
                showResults(data);
            } else {
                alert('Erro: ' + data.error);
                resetUpload();
            }
        })
        .catch(error => {
            progressSection.style.display = 'none';
            alert('Erro no upload: ' + error);
            resetUpload();
        });
    }
    
    function simulateProgress() {
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress >= 90) {
                progress = 90;
                clearInterval(interval);
            }
            progressFill.style.width = progress + '%';
        }, 200);
    }
    
    function showResults(data) {
        document.getElementById('originalDuration').textContent = formatTime(data.original_duration);
        document.getElementById('finalDuration').textContent = formatTime(data.final_duration || data.original_duration);
        document.getElementById('silencesCount').textContent = data.silences_count;
        document.getElementById('timeSaved').textContent = formatTime(data.real_time_saved || data.total_silence_time);
        
        // Calcular e mostrar percentual de redução
        const reductionPercent = data.real_time_saved ? 
            ((data.real_time_saved / data.original_duration) * 100).toFixed(1) : 
            ((data.total_silence_time / data.original_duration) * 100).toFixed(1);
        
        if (document.getElementById('reductionPercent')) {
            document.getElementById('reductionPercent').textContent = reductionPercent + '%';
        }
        
        document.getElementById('reportImage').src = '/report/' + data.report_file;
        
        const downloadBtn = document.getElementById('downloadBtn');
        downloadBtn.onclick = () => {
            window.location.href = '/download/' + data.output_file;
        };
        
        resultsSection.style.display = 'block';
    }
    
    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return mins + ':' + secs.toString().padStart(2, '0');
    }
    
    function resetUpload() {
        uploadArea.style.display = 'block';
        progressSection.style.display = 'none';
        resultsSection.style.display = 'none';
    }
});
