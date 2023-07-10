This repository includes the tool presented in the paper `Wait, wasn't that code here before? Detecting Outdated Software Documentation`. The tool uses GitHub Actions to automate the steps outlined in [DOCER](https://github.com/wesleytanws/DOCER).

### Setup
1. Copy the `DOCER.yml` file containing the workflow to a folder named `.github/workflows` in your project

The tool will automatically scan for outdated code element references whenever a pull request is submitted, and comment on the pull request if outdated references are found.

If you are interested in the project or if you have any questions about the tool, please [send me an email](mailto:wesleytws2018@gmail.com).
