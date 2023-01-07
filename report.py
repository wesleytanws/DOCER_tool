from numpy import where
from pandas import DataFrame, read_csv
from pathlib import Path
import sys

repo_name = sys.argv[1]
run_id = sys.argv[2]

report_outfile = 'output/report.csv'
summary_outfile = 'output/summary.csv'

# Read CSV files from the input directory
matches = read_csv('output/matches.csv', keep_default_na=False)
pages = read_csv('output/pages.csv', keep_default_na=False)
revisions = read_csv('output/revisions.csv', keep_default_na=False)
sources = read_csv('output/sources.csv', keep_default_na=False)

# Link to source code on GitHub
sources = sources.merge(revisions[['page_id', 'rev_id', 'rev_SHA']])
sources = sources.sort_values(by=['rev_id', 'file_name'], ascending=False)
sources = sources.drop_duplicates(subset=['page_id', 'code_element'])
sources['source_link'] = f"https://github.com/{repo_name}/blob/" + \
                        sources['rev_SHA'] + '/' + sources['file_name'] + \
                        '#L' + sources['line_number'].astype(str)

# Reshape revisions as columns, group by pages, select timestamp and SHA
details = revisions[['page_id', 'rev_id', 'rev_SHA', 'rev_timestamp']]
details = details.pivot(index=['page_id'], columns=['rev_id'])

# Rename columns (rev_col, id) as rev_col_id
details.columns = details.columns.map('{0[0]}_{0[1]}'.format)
details_cols = sorted(details.columns.to_list(), \
    key=lambda col_name: int(col_name.split('_')[-1]))

# Combine details in pivot table with the original DataFrame
unique = revisions[['page_id', 'doc_SHA', 'doc_timestamp']].drop_duplicates()
details = DataFrame(details.to_records()).merge(pages).merge(unique)
details = details.reindex(columns=['page_id', 'page_type', 'page_name', \
    *details_cols, 'doc_SHA', 'doc_timestamp'])

# Link to the documentation on GitHub
details['doc_link'] = where(details['page_type'] == 'repo', \

    # Repository
    f"https://github.com/{repo_name}/blob/" + \
    details['doc_SHA'] + '/' + details['page_name'], \

    # Wiki
    f"https://github.com/{repo_name}/wiki/" + \
    details['page_name'].str.rsplit('.', n=1).str[0] + '/' + details['doc_SHA'])

# Reshape revisions as columns, group by code elements and pages
matches = matches.groupby(['code_element', 'page_id', 'rev_id'])['count'].sum().unstack('rev_id')

# Remove rows that are only either 0 or NaN
matches = matches.loc[~(matches.isna() | matches.eq(0)).all(axis=1)]

# Remove files if there are no results
if not len(matches):
    Path(report_outfile).unlink(missing_ok=True)
    Path(summary_outfile).unlink(missing_ok=True)
    sys.exit()

# Rename columns (count, id) as rev_id
matches.columns = ['rev_' + str(col) for col in matches.columns]

# Create columns for missing revisions
rev_cols = [f"rev_{i+1}" for i in range(revisions['rev_id'].max())]
matches = matches.reindex(columns=rev_cols)

# Include these columns in the output
output_cols = ['code_element', 'page_type', 'page_name', *rev_cols, \
    *details_cols, 'doc_SHA', 'doc_timestamp', 'doc_link', 'source_link']

# Combine pivot table with DataFrame as output
report = DataFrame(matches.to_records()).merge(details)
report = report.fillna('.')
report = report.merge(sources[['page_id', 'code_element', 'source_link']], how='left')
report = report.fillna('code_element is a file name')
report = report.sort_values(by=['page_type', 'page_name', 'code_element'])

report.to_csv(report_outfile, columns=output_cols, index=None)

# Filter rows with count that goes to zero
snapshot = report['rev_1'] > 0
current = report['rev_2'] == 0
outdated = report[snapshot & current]

# Remove file if there are no results
if not len(outdated):
    Path(summary_outfile).unlink(missing_ok=True)
    sys.exit()

outdated.to_csv(summary_outfile, columns=output_cols, index=None)

num_outdated_references = len(outdated.index)
max_references_to_show = 10

if num_outdated_references:

    header = f"Merging this pull request may result in {num_outdated_references} outdated {'reference' if num_outdated_references == 1 else 'references'} in the documentation:"

    output_format = DataFrame('- [ ] [' + outdated['page_name'] + '](' + outdated['doc_link'] + \
                    ') - [`' + outdated['code_element'] + '`](' + outdated['source_link'] + ')')

    outdated_references = [outdated_reference.strip() for outdated_reference in output_format.to_string(header=False, index=False, max_colwidth=None).split('\n')]

    partial_references = '\n'.join(outdated_references[:max_references_to_show])
    all_references = '\n'.join(outdated_references)

    with open('output/summary.md', 'w') as f:
        f.write(f"{header}\n\n{all_references}\n")

    print(f"{header}\n\n{partial_references}")

    if num_outdated_references > max_references_to_show: print('... (and more)')

    print(f"\n[View the full report](https://github.com/{repo_name}/actions/runs/{run_id})")
