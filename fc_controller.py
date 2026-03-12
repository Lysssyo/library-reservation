# -*- coding: utf-8 -*-
import sys
import json
import argparse
from config import Config

from alibabacloud_fc20230330.client import Client as FC20230330Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_fc20230330 import models as fc20230330_models
from alibabacloud_tea_util import models as util_models

class FCController:
    @staticmethod
    def create_client() -> FC20230330Client:
        Config.validate_fc()
        config = open_api_models.Config(
            access_key_id=Config.ALIBABA_CLOUD_ACCESS_KEY_ID,
            access_key_secret=Config.ALIBABA_CLOUD_ACCESS_KEY_SECRET
        )
        config.endpoint = Config.FC_ENDPOINT
        return FC20230330Client(config)

    @staticmethod
    def enable_trigger():
        """启用函数计算触发器"""
        client = FCController.create_client()
        runtime = util_models.RuntimeOptions()
        headers = {}
        try:
            print(f"正在启用触发器: {Config.FC_FUNCTION_NAME}...")
            resp = client.enable_function_invocation_with_options(Config.FC_FUNCTION_NAME, headers, runtime)
            print("启用成功:")
            print(json.dumps(resp.to_map(), indent=2))
        except Exception as error:
            print(f"启用失败: {error}")
            if hasattr(error, 'data') and error.data.get("Recommend"):
                print(f"诊断建议: {error.data.get('Recommend')}")
            sys.exit(1)

    @staticmethod
    def disable_trigger():
        """禁用函数计算触发器"""
        client = FCController.create_client()
        disable_request = fc20230330_models.DisableFunctionInvocationRequest(
            reason='Action disabled via GitHub Action',
            abort_ongoing_request=True
        )
        runtime = util_models.RuntimeOptions()
        headers = {}
        try:
            print(f"正在禁用触发器: {Config.FC_FUNCTION_NAME}...")
            resp = client.disable_function_invocation_with_options(Config.FC_FUNCTION_NAME, disable_request, headers, runtime)
            print("禁用成功:")
            print(json.dumps(resp.to_map(), indent=2))
        except Exception as error:
            print(f"禁用失败: {error}")
            if hasattr(error, 'data') and error.data.get("Recommend"):
                print(f"诊断建议: {error.data.get('Recommend')}")
            sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='阿里云 FC 触发器控制器')
    parser.add_argument('action', choices=['enable', 'disable'], help='执行动作: enable 或 disable')
    args = parser.parse_args()

    if args.action == 'enable':
        FCController.enable_trigger()
    elif args.action == 'disable':
        FCController.disable_trigger()
