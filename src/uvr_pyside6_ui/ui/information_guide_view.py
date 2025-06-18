"""View for the Information Guide."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
)

from ..core.logger_utils import get_logger

logger = get_logger(__name__)


class InformationGuideView(QDialog):
    """Dialog for displaying help and information about Ultimate Vocal Remover."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("UVR Information Guide")
        self.setMinimumSize(900, 600)
        self.setModal(False)  # Non-modal so users can keep it open

        main_layout = QVBoxLayout(self)

        # Create splitter for navigation and content
        splitter = QSplitter(Qt.Horizontal)

        # Navigation panel
        self.navigation_list = QListWidget()
        self.navigation_list.setMaximumWidth(250)
        self.navigation_list.currentItemChanged.connect(self._on_topic_changed)

        # Content panel
        self.content_browser = QTextBrowser()
        self.content_browser.setOpenExternalLinks(True)

        splitter.addWidget(self.navigation_list)
        splitter.addWidget(self.content_browser)
        splitter.setStretchFactor(1, 1)  # Give more space to content

        main_layout.addWidget(splitter)

        # Button bar
        button_layout = QHBoxLayout()

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)

        button_layout.addStretch()
        button_layout.addWidget(self.close_button)

        main_layout.addLayout(button_layout)

        # Initialize content
        self._initialize_content()

    def _initialize_content(self):
        """Initialize the help content structure with real UVR information."""
        # Load content from HTML files and add enhanced content
        self.help_content = self._load_help_content()

        # Populate navigation
        for topic in self.help_content.keys():
            self.navigation_list.addItem(topic)

        # Select first item
        if self.navigation_list.count() > 0:
            self.navigation_list.setCurrentRow(0)

    def _load_help_content(self):
        """Load help content from HTML files and create comprehensive content."""
        from pathlib import Path
        
        help_dir = Path(__file__).parent.parent / "resources" / "help"
        
        # Base content structure combining HTML files with enhanced information
        help_content = {
            "Getting Started": """
            <h1>Getting Started with Ultimate Vocal Remover</h1>

            <h2>What is Ultimate Vocal Remover?</h2>
            <p>Ultimate Vocal Remover (UVR) is a powerful, open-source, and cross-platform tool that can separate vocals and instruments from audio files using state-of-the-art AI models. All models provided were trained by UVR core developers.</p>

            <h2>System Requirements</h2>
            <ul>
            <li><strong>Windows:</strong> Windows 10 or later</li>
            <li><strong>macOS:</strong> macOS Big Sur and above</li>
            <li><strong>Linux:</strong> Debian/Ubuntu/Arch-based distributions</li>
            <li><strong>GPU:</strong> Nvidia GTX 1060 6GB minimum for GPU acceleration</li>
            <li><strong>Storage:</strong> 3GB free disk space minimum</li>
            </ul>

            <h2>Quick Start Guide</h2>
            <ol>
            <li><strong>Select Input:</strong> Click "Select Input" to choose your audio file</li>
            <li><strong>Choose Output:</strong> Click "Select Output" to set destination folder</li>
            <li><strong>Select Model:</strong> Choose a processing method (VR Architecture, MDX-Net, or Demucs)</li>
            <li><strong>Download Models:</strong> Use "Download More Models" if needed</li>
            <li><strong>Start Processing:</strong> Click "Start Processing" to begin separation</li>
            </ol>

            <h2>Supported Audio Formats</h2>
            <p><strong>Input:</strong> MP3, FLAC, OGG, WAV, M4A, AAC, WMA, and all FFmpeg-supported formats</p>
            <p><strong>Output:</strong> WAV (16/24/32-bit, Float), FLAC, MP3 (128-320 kbps)</p>
            """,
            "Model Types": """
            <h1>AI Model Types in UVR</h1>

            <h2>VR Architecture Models</h2>
            <p>VR (Vocal Remover) models are excellent for vocal isolation and removal. They offer precise control over the separation process.</p>
            <ul>
            <li><strong>Best for:</strong> Clean vocal removal, karaoke tracks</li>
            <li><strong>Settings:</strong> Window Size, Aggression, Batch Size</li>
            <li><strong>Popular models:</strong> 4_HP-Vocal-UVR, 7_HP2-UVR</li>
            </ul>

            <h2>MDX-Net Models</h2>
            <p>MDX-Net models use advanced neural networks for high-quality source separation with minimal artifacts.</p>
            <ul>
            <li><strong>Best for:</strong> High-quality instrumental separation</li>
            <li><strong>Settings:</strong> Segment Size, Overlap, Pitch Shift</li>
            <li><strong>Popular models:</strong> UVR-MDX-NET Inst 3, UVR-MDX-NET Main</li>
            </ul>

            <h2>Demucs Models</h2>
            <p>Demucs models excel at 4-stem separation (vocals, drums, bass, other) and handle complex music well.</p>
            <ul>
            <li><strong>Best for:</strong> Full band separation, complex arrangements</li>
            <li><strong>Settings:</strong> Segments, Shifts, Overlap</li>
            <li><strong>Popular models:</strong> V4 htdemucs_ft, 6-stem models</li>
            </ul>

            <h2>Model Selection Tips</h2>
            <ul>
            <li>For simple vocal removal: Use VR Architecture models</li>
            <li>For high-quality results: Try MDX-Net models</li>
            <li>For full band separation: Use Demucs 4-stem models</li>
            <li>Experiment with different models for best results</li>
            </ul>
            """,
            "Processing Options": """
            <h1>Processing Options and Settings</h1>

            <h2>Ensemble Mode</h2>
            <p>Ensemble Mode combines multiple AI models for superior results by leveraging the strengths of different architectures.</p>
            <ul>
            <li><strong>Algorithm:</strong> Max Spec, Min Spec, Audio Average, Linear Ensemble</li>
            <li><strong>Main Stem Pair:</strong> Choose primary separation target</li>
            <li><strong>Time Correction:</strong> Aligns timing between models</li>
            </ul>

            <h2>GPU Acceleration</h2>
            <p>Enable GPU processing for significantly faster separation times.</p>
            <ul>
            <li><strong>Requirements:</strong> Nvidia GTX 1060 6GB or better</li>
            <li><strong>Recommended:</strong> 8GB+ VRAM for best performance</li>
            <li><strong>DirectML:</strong> Available for AMD Radeon and Intel Arc GPUs</li>
            </ul>

            <h2>Advanced Settings</h2>
            <h3>VR Architecture</h3>
            <ul>
            <li><strong>Window Size:</strong> 512, 1024, 2048, 4096</li>
            <li><strong>Aggression:</strong> 1-10 (higher = more aggressive separation)</li>
            <li><strong>TTA:</strong> Test Time Augmentation for better quality</li>
            <li><strong>Post Process:</strong> Additional cleanup pass</li>
            </ul>

            <h3>MDX-Net</h3>
            <ul>
            <li><strong>Segment Size:</strong> 256, 512, 1024 (smaller = less VRAM)</li>
            <li><strong>Overlap:</strong> 0.25, 0.5, 0.75, 0.99</li>
            <li><strong>Denoise:</strong> Remove background noise</li>
            <li><strong>Spectral Inversion:</strong> Alternative processing method</li>
            </ul>

            <h3>Demucs</h3>
            <ul>
            <li><strong>Segments:</strong> Memory vs quality trade-off</li>
            <li><strong>Shifts:</strong> Number of random shifts (0-10)</li>
            <li><strong>Split Mode:</strong> Process stems separately</li>
            <li><strong>Combine Stems:</strong> Merge separated stems</li>
            </ul>
            """,
            "Audio Formats": """
            <h1>Audio Formats and Quality</h1>

            <h2>Input Formats</h2>
            <p>UVR supports a wide range of input audio formats through FFmpeg integration:</p>
            <ul>
            <li><strong>Lossless:</strong> WAV, FLAC, AIFF, AU</li>
            <li><strong>Compressed:</strong> MP3, AAC, OGG Vorbis, M4A</li>
            <li><strong>Professional:</strong> BWF, RF64, CAF</li>
            <li><strong>Video:</strong> MP4, AVI, MKV (audio extraction)</li>
            </ul>

            <h2>Output Formats</h2>
            <h3>WAV (Recommended)</h3>
            <ul>
            <li><strong>PCM_16:</strong> 16-bit PCM (standard quality)</li>
            <li><strong>PCM_24:</strong> 24-bit PCM (high quality)</li>
            <li><strong>PCM_32:</strong> 32-bit PCM (maximum quality)</li>
            <li><strong>FLOAT:</strong> 32-bit float (professional)</li>
            </ul>

            <h3>FLAC</h3>
            <ul>
            <li>Lossless compression</li>
            <li>Smaller file sizes than WAV</li>
            <li>Preserves full audio quality</li>
            </ul>

            <h3>MP3</h3>
            <ul>
            <li><strong>320 kbps:</strong> Highest MP3 quality</li>
            <li><strong>256 kbps:</strong> Very good quality</li>
            <li><strong>128 kbps:</strong> Standard quality</li>
            </ul>

            <h2>Quality Recommendations</h2>
            <ul>
            <li><strong>Archival:</strong> Use FLAC or WAV PCM_24</li>
            <li><strong>Mastering:</strong> Use WAV FLOAT or PCM_32</li>
            <li><strong>Distribution:</strong> Use MP3 320 kbps</li>
            <li><strong>Streaming:</strong> Use MP3 256 kbps</li>
            </ul>
            """,
            "Troubleshooting": """
            <h1>Troubleshooting Common Issues</h1>

            <h2>Memory Errors</h2>
            <p><strong>Symptoms:</strong> "Out of memory" or allocation errors</p>
            <p><strong>Solutions:</strong></p>
            <ul>
            <li>Lower the Segment size (MDX-Net) or Window size (VR Architecture)</li>
            <li>Reduce Batch Size in advanced settings</li>
            <li>Close other applications to free up RAM/VRAM</li>
            <li>Use CPU processing instead of GPU if VRAM is limited</li>
            </ul>

            <h2>Poor Separation Quality</h2>
            <p><strong>Symptoms:</strong> Vocals bleeding through, artifacts, distortion</p>
            <p><strong>Solutions:</strong></p>
            <ul>
            <li>Try different models - each works better on different music types</li>
            <li>Use Ensemble Mode with multiple models</li>
            <li>Adjust Aggression setting (VR Architecture)</li>
            <li>Enable TTA (Test Time Augmentation) for better quality</li>
            <li>Check that input audio is high quality (avoid low bitrate MP3s)</li>
            </ul>

            <h2>Slow Processing</h2>
            <p><strong>Symptoms:</strong> Very long processing times</p>
            <p><strong>Solutions:</strong></p>
            <ul>
            <li>Enable GPU acceleration if you have a compatible GPU</li>
            <li>Increase Segment size (if you have enough VRAM)</li>
            <li>Disable TTA for faster processing</li>
            <li>Use smaller models for testing</li>
            </ul>

            <h2>Model Download Issues</h2>
            <p><strong>Symptoms:</strong> Models fail to download or are corrupted</p>
            <p><strong>Solutions:</strong></p>
            <ul>
            <li>Check your internet connection</li>
            <li>Try refreshing the model catalog</li>
            <li>Clear browser cache if using web version</li>
            <li>Download models manually from the official repository</li>
            </ul>

            <h2>FFmpeg Errors</h2>
            <p><strong>Symptoms:</strong> Cannot process non-WAV files</p>
            <p><strong>Solutions:</strong></p>
            <ul>
            <li>Ensure FFmpeg is properly installed</li>
            <li>Convert input files to WAV format first</li>
            <li>Check file permissions and path</li>
            <li>Reinstall UVR with FFmpeg included</li>
            </ul>
            """,
            "VIP Features": """
            <h1>VIP Features and Premium Models</h1>

            <h2>What is VIP Access?</h2>
            <p>VIP Access unlocks premium features and exclusive AI models trained by the UVR development team.</p>

            <h2>VIP Benefits</h2>
            <ul>
            <li><strong>Premium Models:</strong> Access to 50+ exclusive high-quality AI models</li>
            <li><strong>Early Access:</strong> Get experimental models before public release</li>
            <li><strong>Commercial Rights:</strong> Use VIP models for commercial projects</li>
            <li><strong>Priority Support:</strong> Faster response times for technical issues</li>
            <li><strong>Advanced Algorithms:</strong> Cutting-edge separation techniques</li>
            </ul>

            <h2>How to Get VIP Access</h2>
            <ol>
            <li><strong>Support the Project:</strong> Become a Patreon supporter</li>
            <li><strong>Contribute:</strong> Help with development or documentation</li>
            <li><strong>Purchase License:</strong> Buy commercial VIP license</li>
            <li><strong>Community:</strong> Active contributors may receive codes</li>
            </ol>

            <h2>VIP Model Categories</h2>
            <ul>
            <li><strong>VR Architecture VIP:</strong> Enhanced vocal removal models</li>
            <li><strong>MDX-Net VIP:</strong> Premium instrumental separation</li>
            <li><strong>MDX23C VIP:</strong> Latest generation MDX models</li>
            <li><strong>Demucs VIP:</strong> Advanced 4-stem and 6-stem models</li>
            </ul>

            <h2>Activating VIP Access</h2>
            <ol>
            <li>Obtain a valid VIP access code from the UVR team</li>
            <li>Go to Download Center → VIP Access</li>
            <li>Enter your VIP code</li>
            <li>Refresh the model catalog to see premium models</li>
            </ol>

            <p><strong>Note:</strong> VIP codes use cryptographic verification and are provided exclusively by the UVR development team.</p>
            """,
            "FAQ": """
            <h1>Frequently Asked Questions</h1>

            <h2>General Questions</h2>

            <h3>Q: Is Ultimate Vocal Remover free?</h3>
            <p>A: Yes, UVR is completely free and open-source. VIP features are available for supporters and commercial users.</p>

            <h3>Q: How long does processing take?</h3>
            <p>A: Processing time varies based on:</p>
            <ul>
            <li>Audio length (3-4 minutes typical)</li>
            <li>Hardware (GPU much faster than CPU)</li>
            <li>Model complexity</li>
            <li>Settings used</li>
            </ul>
            <p>Typical times: 30 seconds to 5 minutes for a 3-minute song.</p>

            <h3>Q: Can I process multiple files at once?</h3>
            <p>A: Yes, UVR supports batch processing. Select multiple files or an entire folder.</p>

            <h2>Technical Questions</h2>

            <h3>Q: Which GPU is recommended?</h3>
            <p>A: Nvidia GTX 1060 6GB minimum, RTX series recommended. 8GB+ VRAM ideal for best performance.</p>

            <h3>Q: Can I use AMD GPUs?</h3>
            <p>A: Limited support via DirectML. Nvidia GPUs provide best performance and compatibility.</p>

            <h3>Q: Why does separation quality vary?</h3>
            <p>A: Quality depends on:</p>
            <ul>
            <li>Original audio quality</li>
            <li>Music complexity (simple vs dense arrangements)</li>
            <li>Model selection</li>
            <li>Settings optimization</li>
            </ul>

            <h2>Usage Questions</h2>

            <h3>Q: How do I get better results?</h3>
            <p>A: Try these approaches:</p>
            <ul>
            <li>Use high-quality input audio (FLAC, high-bitrate MP3)</li>
            <li>Experiment with different models</li>
            <li>Use Ensemble Mode with multiple models</li>
            <li>Adjust advanced settings for your specific audio</li>
            </ul>

            <h3>Q: Can I separate more than vocals?</h3>
            <p>A: Yes! Demucs models can separate:</p>
            <ul>
            <li>Vocals</li>
            <li>Drums</li>
            <li>Bass</li>
            <li>Other instruments</li>
            <li>Some models support 6-stem separation</li>
            </ul>

            <h3>Q: Is there a file size limit?</h3>
            <p>A: No strict limit, but very long files may require more VRAM/RAM and take longer to process.</p>

            <h2>Support</h2>

            <h3>Q: Where can I get help?</h3>
            <p>A: Support is available through:</p>
            <ul>
            <li>GitHub Issues page</li>
            <li>Community forums</li>
            <li>Discord server</li>
            <li>Error Log (in Settings Guide)</li>
            </ul>

            <h3>Q: How do I report bugs?</h3>
            <p>A: Please provide:</p>
            <ul>
            <li>Detailed description of the issue</li>
            <li>Error log information</li>
            <li>System specifications</li>
            <li>Steps to reproduce</li>
            </ul>
            """,
        }

        return help_content

    def _on_topic_changed(self, current, previous):
        """Handle topic selection change."""
        if current:
            topic = current.text()
            content = self.help_content.get(topic, "<h1>Content not available</h1>")

            # Set HTML content directly
            self.content_browser.setHtml(content)

            # Scroll to top
            cursor = self.content_browser.textCursor()
            cursor.movePosition(QTextCursor.Start)
            self.content_browser.setTextCursor(cursor)

    def show_topic(self, topic_name):
        """Show a specific topic."""
        # Find and select the topic in the navigation
        for i in range(self.navigation_list.count()):
            item = self.navigation_list.item(i)
            if item.text() == topic_name:
                self.navigation_list.setCurrentItem(item)
                break
