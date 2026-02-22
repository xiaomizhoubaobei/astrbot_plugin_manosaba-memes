#!/bin/bash

# 定义颜色代码
PINK='\033[1;35m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# 安装typescript专家智能体
iflow agent add "typescript-pro" --scope global
echo -e "${PINK}typescript专家智能体安装完成${NC}"

# 安装教程编写专家智能体
iflow agent add "tutorial-engineer" --scope global
echo -e "${PINK}教程编写专家智能体安装完成${NC}"

# 安装文档架构师智能体
iflow agent add "docs-architect" --scope global
echo -e "${PINK}文档架构师智能体安装完成${NC}"

# 安装后端架构师智能体
iflow agent add "backend-architect" --scope global
echo -e "${PINK}后端架构师智能体安装完成${NC}"

# 安装代码审查专家智能体
iflow agent add "code-reviewer" --scope global
echo -e "${PINK}代码审查专家智能体安装完成${NC}"

# 安装安全审计专家智能体
iflow agent add "security-auditor" --scope global
echo -e "${PINK}安全审计专家智能体安装完成${NC}"

# 安装架构师审查专家智能体
iflow agent add "architect-reviewer" --scope global
echo -e "${PINK}架构师审查专家智能体安装完成${NC}"

# 安装API文档专家智能体
iflow agent add "api-documenter" --scope global
echo -e "${PINK}API文档专家智能体安装完成${NC}"

# 安装HTML编写专家智能体
iflow agent add "format_html_agent" --scope global
echo -e "${PINK}HTML编写专家智能体安装完成${NC}"

# 安装错误检测专家智能体
iflow agent add "error-detective" --scope global
echo -e "${PINK}错误检测专家智能体安装完成${NC}"

# 安装遗留代码专家智能体
iflow agent add "legacy-modernizer" --scope global
echo -e "${PINK}遗留代码专家智能体安装完成${NC}"

# 安装前端开发专家智能体
iflow agent add "frontend-developer" --scope global
echo -e "${PINK}前端开发专家智能体安装完成${NC}"

# 安装调试专家智能体
iflow agent add "debugger" --scope global
echo -e "${PINK}调试专家智能体安装完成${NC}"

# 安装性能专家智能体
iflow agent add "performance-engineer" --scope global
echo -e "${PINK}性能专家智能体安装完成${NC}"