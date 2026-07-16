"""技能执行引擎 — 支持 Python函数 / API调用 / Prompt模板 三种方式，支持链式传递"""
import json
import logging
import importlib
import urllib.parse

logger = logging.getLogger("skill_executor")


class SkillExecutor:
    """技能执行器，根据技能的 impl_type 执行对应逻辑"""

    @staticmethod
    def execute(skill, input_params=None):
        """
        执行单个技能
        :param skill: dict, 技能记录（含 impl_type, impl_config, input_schema 等）
        :param input_params: dict, 输入参数（可从上一技能输出链式传入）
        :return: dict {"success": bool, "data": any, "error": str}
        """
        if not skill or not skill.get("status"):
            return {"success": False, "error": "技能未启用或不存在"}

        impl_type = skill.get("impl_type", "prompt")
        impl_config = skill.get("impl_config", {})
        if isinstance(impl_config, str):
            impl_config = json.loads(impl_config)

        try:
            if impl_type == "python_func":
                return SkillExecutor._exec_python_func(impl_config, input_params or {})
            elif impl_type == "api_call":
                return SkillExecutor._exec_api_call(impl_config, input_params or {})
            elif impl_type == "prompt":
                return SkillExecutor._exec_prompt(impl_config, input_params or {})
            else:
                return {"success": False, "error": f"未知的技能实现方式: {impl_type}"}
        except Exception as e:
            logger.error(f"技能执行失败 [{skill.get('name')}]: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def execute_chain(skills, initial_input=None):
        """
        链式执行多个技能，前一技能的输出作为后一技能的输入
        :param skills: list[dict], 技能记录列表（按执行顺序排列）
        :param initial_input: dict, 初始输入参数
        :return: dict {"success": bool, "results": list, "final_output": any}
        """
        results = []
        current_input = initial_input or {}

        for skill in skills:
            result = SkillExecutor.execute(skill, current_input)
            results.append({
                "skill_name": skill.get("name"),
                "skill_code": skill.get("code"),
                "success": result["success"],
                "data": result.get("data"),
                "error": result.get("error")
            })
            if result["success"]:
                current_input = result.get("data", {})
                if isinstance(current_input, str):
                    current_input = {"_output": current_input}
            else:
                break

        return {
            "success": all(r["success"] for r in results),
            "results": results,
            "final_output": current_input if results and results[-1]["success"] else None
        }

    # ---- 内部实现 ----

    @staticmethod
    def _exec_python_func(config, params):
        """通过 importlib 动态加载模块并调用函数"""
        module_path = config.get("module_path", "")
        func_name = config.get("func_name", "")
        if not module_path or not func_name:
            return {"success": False, "error": "缺少 module_path 或 func_name"}

        try:
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
            result = func(**params) if params else func()
            return {"success": True, "data": result}
        except ImportError as e:
            return {"success": False, "error": f"模块加载失败: {e}"}
        except AttributeError:
            return {"success": False, "error": f"函数 {func_name} 在模块 {module_path} 中不存在"}
        except TypeError as e:
            return {"success": False, "error": f"函数参数不匹配: {e}"}

    @staticmethod
    def _exec_api_call(config, params):
        """发起 HTTP 请求调用外部 API"""
        import requests

        url = config.get("url", "")
        method = config.get("method", "GET").upper()
        headers = config.get("headers", {})
        param_template = config.get("params", {})

        if not url:
            return {"success": False, "error": "缺少 API URL"}

        # 模板变量替换
        filled_url = url
        filled_params = {}
        for k, v in param_template.items():
            filled_params[k] = v
            if isinstance(v, str) and "{" in v:
                for p_key, p_val in params.items():
                    filled_params[k] = filled_params[k].replace(f"{{{p_key}}}", str(p_val))

        try:
            if method == "GET":
                resp = requests.get(filled_url, headers=headers, params=filled_params, timeout=15)
            elif method == "POST":
                resp = requests.post(filled_url, headers=headers, json=filled_params, timeout=15)
            else:
                return {"success": False, "error": f"不支持的 HTTP 方法: {method}"}

            if resp.status_code >= 400:
                return {"success": False, "error": f"API 返回错误: {resp.status_code}"}

            content_type = resp.headers.get("Content-Type", "")
            if "json" in content_type:
                return {"success": True, "data": resp.json()}
            return {"success": True, "data": resp.text}
        except Exception as e:
            return {"success": False, "error": f"API 请求失败: {e}"}

    @staticmethod
    def _exec_prompt(config, params):
        """渲染 Prompt 模板（变量替换后返回提示词文本）"""
        system_prompt = config.get("system_prompt", "")
        user_template = config.get("user_template", "")

        # 模板变量替换
        result_system = system_prompt
        result_user = user_template
        for k, v in params.items():
            placeholder = f"{{{k}}}"
            result_system = result_system.replace(placeholder, str(v))
            result_user = result_user.replace(placeholder, str(v))

        return {
            "success": True,
            "data": {
                "system_prompt": result_system,
                "user_prompt": result_user
            }
        }
