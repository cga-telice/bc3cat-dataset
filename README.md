# BC3CAT Dataset: A Benchmark for Retrieval on Parametric Construction Catalogs

This repository contains the data processing pipeline for creating a retrieval evaluation benchmark from ADIF's parametric construction price catalog. The dataset is part of the research presented in:

> **A Systematic Comparative Study of Retrieval Methods for Parametric Construction Catalogs: From Lexical to Neural Approaches**  
> González-Alvarez, C., Fernández-Robles, L., Alegre, E., & Castejón-Limas, M.  
> *Automation in Construction* (under review)

## Overview

This pipeline transforms raw BC3/FIEBDC format files from ADIF's (Spanish Railway Infrastructure Administrator) price catalog into a structured retrieval benchmark. The resulting dataset enables evaluation of information retrieval methods for construction catalog matching, where:

- **Queries**: Short-format descriptions (*resumen*) — condensed summaries of construction work items
- **Documents**: Long-format descriptions (*texto*) — detailed technical specifications
- **Task**: Given a short description, retrieve the matching long description from ~47,000 candidates

### Dataset Characteristics

| Characteristic | Value |
|----------------|-------|
| Total unique items | 47,513 |
| Base templates | 30 |
| Average expansion factor | 1,583.8× |
| Short-format mean length | 19.7 words |
| Long-format mean length | 84.5 words |
| Items with numeric parameters | 99.8% |

## Repository Structure

```
bc3cat-dataset/
├── data/
│   ├── raw/                          # Original BC3 format files
│   │   └── BPA_2024_v2_OEB_mod_utf8.txt
│   ├── intermediate/                 # Processing stage outputs
│   │   ├── BPA_2024_v2_OEB_mod_utf8.json
│   │   ├── ARQUITECTURA/
│   │   ├── OBRA CIVIL/
│   │   ├── ENERGIA/
│   │   └── ...                       # Other chapters
│   └── processed/                    # Final dataset files
│       ├── OEB_resumen.pkl           # Query documents (short-format)
│       ├── OEB_texto.pkl             # Target documents (long-format)
│       ├── OEB_resumen.json          # JSON export
│       └── OEB_texto.json            # JSON export
├── src/
│   ├── s01_parse_fiebdc.ipynb        # BC3 format parser
│   ├── s02_split_chapters.ipynb      # Chapter separation
│   ├── s03_generate_parametric_combinations.ipynb
│   ├── s04_evaluate_text_variables.ipynb
│   ├── s05_evaluate_resumen_texto.ipynb
│   ├── s06_data_analysis.ipynb
│   ├── s07_Filter duplicates.ipynb
│   ├── s08_Llamaindex_Doc_Creation.ipynb
│   ├── Generate_OEB_dataset.ipynb    # Complete OEB extraction
│   └── utils/
│       ├── config.py
│       ├── custom_types.py
│       ├── data_utils.py
│       ├── evaluation.py
│       ├── index_classes.py
│       ├── text_processing.py
│       └── z_formula_processing.py
├── DataInBrief_BC3CAT.docx # "Data in brief" paper manuscript
├── docker-compose.yml
└── README.md
```

## Data Pipeline

The pipeline transforms BC3 catalog files through eight sequential stages:

### Stage 1: Parse FIEBDC/BC3 Format (`s01_parse_fiebdc.ipynb`)

Parses the raw BC3 file (FIEBDC-3/2016 standard) into structured JSON. Handles:
- Concept definitions (`~C` records)
- Parameter specifications (`~P` records)
- Text variables and formulas
- RESUMEN (short-format) and TEXTO (long-format) fields

**Input**: `data/raw/BPA_2024_v2_OEB_mod_utf8.txt`  
**Output**: `data/intermediate/BPA_2024_v2_OEB_mod_utf8.json`

### Stage 2: Split by Chapters (`s02_split_chapters.ipynb`)

Separates the monolithic catalog into technical chapters:
- ARQUITECTURA (Architecture)
- OBRA CIVIL (Civil Works) ← *contains OEB subcategory*
- CONTROL MANDO Y SEÑALIZACIÓN (Control & Signaling)
- ENERGIA (Energy)
- GESTIÓN AMBIENTAL (Environmental Management)
- PROTECCIÓN Y SEGURIDAD (Protection & Security)
- SEGURIDAD Y SALUD (Safety & Health)
- TELECOMUNICACIONES (Telecommunications)
- VIA (Railway Track)
- PRECIOS BÁSICOS (Basic Prices)

**Output**: `data/intermediate/{CHAPTER}/{CHAPTER}.json`

### Stage 3: Generate Parametric Combinations (`s03_generate_parametric_combinations.ipynb`)

Expands parametric templates into concrete item variants. A single base template like "Concrete-encased PVC conduit" generates hundreds of variants by combining:
- Pipe quantities (2, 4, 6, 8, 12)
- Diameters (110mm, 160mm, 200mm)
- Terrain types (normal, rocky, under tracks, road crossing, platform, ballast)
- Work shifts (daytime, nighttime, exceptional)
- Maintenance windows and execution conditions

### Stage 4: Evaluate Text Variables (`s04_evaluate_text_variables.ipynb`)

Resolves formula-based text variables embedded in descriptions. The BC3 format supports conditional text generation based on parameter values.

### Stage 5: Generate Resumen/Texto Pairs (`s05_evaluate_resumen_texto.ipynb`)

Produces the final query-document pairs:
- **resumen**: Condensed description used as retrieval query
- **texto**: Full technical specification used as retrieval target

### Stage 6: Data Analysis (`s06_data_analysis.ipynb`)

Statistical analysis of the generated dataset including:
- Length distributions
- Parameter coverage
- Hierarchical structure validation

### Stage 7: Filter Duplicates (`s07_Filter duplicates.ipynb`)

Removes duplicate entries that may arise from parameter combination edge cases.

### Stage 8: Create LlamaIndex Documents (`s08_Llamaindex_Doc_Creation.ipynb`)

Converts processed data into LlamaIndex `Document` objects with metadata:
- `item_key`: Unique identifier (e.g., "OEB020$AAAAAA")
- `parent_key`: Base template identifier (first 6 characters)
- `text`: Document content (resumen or texto)

## Quick Start

### Prerequisites

- Docker with NVIDIA GPU support (recommended)
- Or: Python 3.11+ with dependencies

### Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/[username]/bc3cat-dataset.git
cd bc3cat-dataset

# Start Jupyter environment
docker-compose up -d

# Access Jupyter at http://localhost:8888 (token: j)
```

### Manual Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install jupyter pandas numpy scipy scikit-learn llama-index

# Run notebooks in order
cd src
jupyter notebook
```

### Generate the OEB Dataset

Run the pipeline stages sequentially:

```bash
# In Jupyter, run notebooks in order:
src/s01_parse_fiebdc.ipynb
src/s02_split_chapters.ipynb
src/s03_generate_parametric_combinations.ipynb
src/s04_evaluate_text_variables.ipynb
src/s05_evaluate_resumen_texto.ipynb
src/s06_data_analysis.ipynb
src/s07_Filter duplicates.ipynb
src/s08_Llamaindex_Doc_Creation.ipynb
```

After the full pipeline has been executed, you can extract the OEB subcategory subset using:

```bash
# Filters OEB items from the processed OBRA CIVIL chapter
src/Generate_OEB_dataset.ipynb
```

This notebook loads the processed `OBRA CIVIL_texto.pkl` and extracts only items with keys starting with "OEB".

## Data Formats

### Pickle Files (`.pkl`)

LlamaIndex Document objects with the following structure:

```python
Document(
    text="Canalización hormigonada de 2 tubos...",  # Content
    metadata={
        "item_key": "OEB020$AAAAAA",  # Unique identifier
        "parent_key": "OEB020",        # Base template
        "ud": "m"                      # Unit of measure
    }
)
```

### JSON Files

```json
{
    "OEB020$AAAAAA": {
        "item_key": "OEB020$AAAAAA",
        "text": "Canalización hormigonada de 2 tubos...",
        "parent_key": "OEB020",
        "ud": "m"
    }
}
```

## BC3/FIEBDC Format Reference

The BC3 format (Base de Costes de la Construcción) is the Spanish standard for construction cost database interchange, maintained by [FIEBDC](https://www.fiebdc.es/). Key record types:

| Record | Description |
|--------|-------------|
| `~V` | Version header |
| `~K` | Configuration parameters |
| `~C` | Concept definition (item) |
| `~P` | Parameter definition |
| `~T` | Text block (RESUMEN/TEXTO) |

For full specification, see: [FIEBDC-3/2016](https://www.fiebdc.es/fiebdc-32016-2/)

## Citation

If you use this dataset in your research, please cite:

```bibtex
@article{gonzalez2025systematic,
  title={A Systematic Comparative Study of Retrieval Methods for Parametric Construction Catalogs: From Lexical to Neural Approaches},
  author={González-Alvarez, Cesáreo and Fernández-Robles, Laura and Alegre, Enrique and Castejón-Limas, Manuel},
  journal={Automation in Construction},
  year={2025},
  note={Under review}
}
```

## Acknowledgments

- **ADIF** (Administrador de Infraestructuras Ferroviarias) for the source catalog data
- **Telice S.A.** for providing resources and data access
- **FIEBDC** for the BC3 format specification

## License

This repository uses dual licensing:

### Code (MIT License)

The source code (notebooks, scripts, utilities) is licensed under the MIT License:

```
MIT License

Copyright (c) 2025 Cesáreo González-Alvarez, Universidad de León

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### Dataset (CC-BY 4.0)

The processed dataset files are licensed under [Creative Commons Attribution 4.0 International (CC-BY 4.0)](https://creativecommons.org/licenses/by/4.0/).

You are free to:
- **Share** — copy and redistribute the material in any medium or format
- **Adapt** — remix, transform, and build upon the material for any purpose, including commercial

Under the following terms:
- **Attribution** — You must give appropriate credit, provide a link to the license, and indicate if changes were made. Please cite our paper (see Citation section above).

The source data is derived from ADIF's public price catalog (Base de Precios ADIF).

## Contact

Cesáreo González-Alvarez  
Universidad de León  
Email: cgonza06@estudiantes.unileon.es
