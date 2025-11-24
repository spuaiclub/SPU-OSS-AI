SPU-OSS AI Chat App
===================

A modern, responsive desktop chat application built with **PyQt6**. It now supports multiple AI providers including **ChatGPT, Gemini, DeepSeek, and Perplexity**.

Features / คุณสมบัติ
--------------------

-   **Multi-Provider Support**: Switch between OpenAI, Google Gemini, DeepSeek, and Perplexity.

-   **Thai Comments**: Code includes comments in Thai for easier learning.

-   **Modern UI**: macOS-inspired design with Markdown support.

-   **Secure Key Storage**: API Keys are stored locally on your device.

Prerequisites / สิ่งที่ต้องเตรียม
---------------------------------

You need Python installed. Then, install the required libraries:

```
pip install PyQt6 requests markdown

```

How to Run / วิธีใช้งาน
-----------------------

1.  Run the application:

    ```
    python spu_oss_ai.py

    ```

2.  Click **Settings (⚙️)**.

3.  Select your Provider (e.g., DeepSeek).

4.  Paste your API Key in the corresponding field.

5.  Click **Save** and start chatting!

Supported APIs / API ที่รองรับ
------------------------------

|

Provider

 |

Model Used

 |

Notes

 |
|

**OpenAI**

 |

`gpt-4o-mini`

 |

Standard ChatGPT API

 |
|

**Gemini**

 |

`gemini-1.5-flash`

 |

Uses Google's REST API (Key required)

 |
|

**DeepSeek**

 |

`deepseek-chat`

 |

OpenAI-Compatible Endpoint

 |
|

**Perplexity**

 |

`llama-3.1-sonar`

 |

Optimized for search/reasoning

 |
