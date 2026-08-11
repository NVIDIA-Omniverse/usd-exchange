// SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#include "usdex/core/Diagnostics.h"

#include "usdex/core/Settings.h"

#include <pxr/base/arch/debugger.h>
#include <pxr/base/tf/stackTrace.h>

using namespace pxr;

namespace
{

class DiagnosticsDelegate final : TfDiagnosticMgr::Delegate
{
public:

    DiagnosticsDelegate()
        : m_active(false), m_level(usdex::core::DiagnosticsLevel::eWarning), m_outputStream(usdex::core::DiagnosticsOutputStream::eStderr)
    {
    }

    ~DiagnosticsDelegate() = default;

    static DiagnosticsDelegate* acquire()
    {
        static std::unique_ptr<DiagnosticsDelegate> s_delegate = std::make_unique<DiagnosticsDelegate>();
        return s_delegate.get();
    }

    bool isActive()
    {
        return m_active;
    }

    void activate()
    {
        if (!m_active)
        {
            TfDiagnosticMgr::GetInstance().AddDelegate(this);
            m_active = true;
        }
    }

    void deactivate()
    {
        if (m_active)
        {
            TfDiagnosticMgr::GetInstance().RemoveDelegate(this);
            m_active = false;
        }
    }

    void setLevel(usdex::core::DiagnosticsLevel value)
    {
        m_level = value;
    }

    usdex::core::DiagnosticsLevel getLevel()
    {
        return m_level;
    }

    void setOutputStream(usdex::core::DiagnosticsOutputStream value)
    {
        m_outputStream = value;
    }

    usdex::core::DiagnosticsOutputStream getOutputStream()
    {
        return m_outputStream;
    }

    void IssueError(const TfError& err) override
    {
        if (m_level < usdex::core::DiagnosticsLevel::eError)
        {
            return;
        }

        printDiagnostic(err);
    }

    void IssueFatalError(const TfCallContext& context, const std::string& msg) override
    {
        // This is invoked when TF_FATAL_CODING_ERROR or TF_FATAL_ERROR are emitted.
        // We simply print the message to the configured output stream. Afterwards
        // TfDiagnosticMgr will log the crash and terminate the process.
        if (context.IsHidden())
        {
            print(TfStringPrintf("[Fatal] %s\n", msg.c_str()));
        }
        else
        {
            print(TfStringPrintf("[Fatal] [%s] %s\n", context.GetPrettyFunction(), msg.c_str()));
        }
    }

    void IssueStatus(const TfStatus& status) override
    {
        if (m_level < usdex::core::DiagnosticsLevel::eStatus)
        {
            return;
        }

        printDiagnostic(status);
    }

    void IssueWarning(const TfWarning& warning) override
    {
        if (m_level < usdex::core::DiagnosticsLevel::eWarning)
        {
            return;
        }

        printDiagnostic(warning);
    }

private:

    std::string formatDiagnostic(const TfDiagnosticBase& diagnostic)
    {
        // It is possible for diagnostics to be emitted without any information in the call context,
        // in which case we should avoid adding that extra context in our diagnostic.
        // In particular this occurs for TfStatus emitted from python with verbose=False,
        // though it is possible there are other circumstances as well.
        if (diagnostic.GetContext().IsHidden() || diagnostic.GetSourceFileName().empty())
        {
            return TfStringPrintf(
                "[%s] %s\n",
                TfDiagnosticMgr::GetCodeName(diagnostic.GetDiagnosticCode()).c_str(),
                diagnostic.GetCommentary().c_str()
            );
        }
        else
        {
            return TfStringPrintf(
                "[%s] [%s] %s\n",
                TfDiagnosticMgr::GetCodeName(diagnostic.GetDiagnosticCode()).c_str(),
                diagnostic.GetSourceFunction().c_str(),
                diagnostic.GetCommentary().c_str()
            );
        }
    }

    void printDiagnostic(const TfDiagnosticBase& diagnostic)
    {
        if (m_outputStream == usdex::core::DiagnosticsOutputStream::eNone || diagnostic.GetQuiet())
        {
            return;
        }

        FILE* ostream = (m_outputStream == usdex::core::DiagnosticsOutputStream::eStderr) ? stderr : stdout;
        fprintf(ostream, "%s", formatDiagnostic(diagnostic).c_str());
    }

    void print(const std::string& message)
    {
        if (m_outputStream == usdex::core::DiagnosticsOutputStream::eNone)
        {
            return;
        }

        FILE* ostream = (m_outputStream == usdex::core::DiagnosticsOutputStream::eStderr) ? stderr : stdout;
        fprintf(ostream, "%s", message.c_str());
    }

    bool m_active;
    usdex::core::DiagnosticsLevel m_level;
    usdex::core::DiagnosticsOutputStream m_outputStream;
};

} // namespace

bool usdex::core::isDiagnosticsDelegateActive()
{
    return ::DiagnosticsDelegate::acquire()->isActive();
}

void usdex::core::activateDiagnosticsDelegate()
{
    ::DiagnosticsDelegate::acquire()->activate();
}

void usdex::core::deactivateDiagnosticsDelegate()
{
    ::DiagnosticsDelegate::acquire()->deactivate();
}

void usdex::core::setDiagnosticsLevel(usdex::core::DiagnosticsLevel value)
{
    ::DiagnosticsDelegate::acquire()->setLevel(value);
}

usdex::core::DiagnosticsLevel usdex::core::getDiagnosticsLevel()
{
    return ::DiagnosticsDelegate::acquire()->getLevel();
}

usdex::core::DiagnosticsLevel usdex::core::getDiagnosticLevel(TfDiagnosticType code)
{
    switch (code)
    {
        case TF_DIAGNOSTIC_STATUS_TYPE:
            return usdex::core::DiagnosticsLevel::eStatus;
        case TF_DIAGNOSTIC_WARNING_TYPE:
            return usdex::core::DiagnosticsLevel::eWarning;
        case TF_DIAGNOSTIC_CODING_ERROR_TYPE:
        case TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE:
        case TF_DIAGNOSTIC_NONFATAL_ERROR_TYPE:
            return usdex::core::DiagnosticsLevel::eError;
        case TF_DIAGNOSTIC_FATAL_CODING_ERROR_TYPE:
        case TF_DIAGNOSTIC_FATAL_ERROR_TYPE:
        case TF_APPLICATION_EXIT_TYPE:
            return usdex::core::DiagnosticsLevel::eFatal;
        default:
            // TF_DIAGNOSTIC_INVALID_TYPE is not a valid diagnostic level so we fallback to status
            return usdex::core::DiagnosticsLevel::eStatus;
    }
}

void usdex::core::setDiagnosticsOutputStream(usdex::core::DiagnosticsOutputStream value)
{
    ::DiagnosticsDelegate::acquire()->setOutputStream(value);
}

usdex::core::DiagnosticsOutputStream usdex::core::getDiagnosticsOutputStream()
{
    return ::DiagnosticsDelegate::acquire()->getOutputStream();
}
